use std::collections::HashMap;
use std::fmt::{Display, Formatter};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SkillManifest {
    pub name: String,
    pub version: String,
    pub description: String,
    pub author: Option<String>,
    pub tags: Vec<String>,
    pub system_prompt_fragment: Option<String>,
    pub tool_names: Vec<String>,
    pub config: HashMap<String, String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SkillError {
    NotFound(String),
    ParseError(String),
    IoError(String),
}

impl Display for SkillError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NotFound(message) | Self::ParseError(message) | Self::IoError(message) => {
                write!(f, "{message}")
            }
        }
    }
}

impl std::error::Error for SkillError {}

pub struct SkillRegistry {
    skills: HashMap<String, SkillManifest>,
    search_paths: Vec<PathBuf>,
}

impl SkillRegistry {
    #[must_use]
    pub fn new() -> Self {
        Self {
            skills: HashMap::new(),
            search_paths: Vec::new(),
        }
    }

    pub fn add_search_path(&mut self, path: PathBuf) {
        self.search_paths.push(path);
    }

    pub fn load_from_dirs(&mut self) -> Result<usize, SkillError> {
        let mut loaded = 0usize;
        for search_path in &self.search_paths {
            let entries = match fs::read_dir(search_path) {
                Ok(entries) => entries,
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => continue,
                Err(error) => {
                    return Err(SkillError::IoError(format!(
                        "{}: {error}",
                        search_path.display()
                    )))
                }
            };
            for entry in entries {
                let entry = entry.map_err(|error| SkillError::IoError(error.to_string()))?;
                let path = entry.path();
                if !path.is_file()
                    || path.extension().and_then(|extension| extension.to_str()) != Some("toml")
                {
                    continue;
                }
                let manifest = load_skill_manifest(&path)?;
                self.skills.insert(manifest.name.clone(), manifest);
                loaded += 1;
            }
        }
        Ok(loaded)
    }

    #[must_use]
    pub fn get(&self, name: &str) -> Option<&SkillManifest> {
        self.skills.get(name)
    }

    #[must_use]
    pub fn list(&self) -> Vec<&SkillManifest> {
        let mut values = self.skills.values().collect::<Vec<_>>();
        values.sort_by(|left, right| left.name.cmp(&right.name));
        values
    }

    #[must_use]
    pub fn system_prompt_fragments(&self, active: &[String]) -> String {
        active
            .iter()
            .filter_map(|name| self.get(name))
            .filter_map(|manifest| manifest.system_prompt_fragment.as_deref())
            .collect::<Vec<_>>()
            .join("\n\n")
    }

    #[cfg(test)]
    pub(crate) fn insert_for_tests(&mut self, manifest: SkillManifest) {
        self.skills.insert(manifest.name.clone(), manifest);
    }
}

pub fn load_skill_manifest(path: &Path) -> Result<SkillManifest, SkillError> {
    let contents = fs::read_to_string(path)
        .map_err(|error| SkillError::IoError(format!("{}: {error}", path.display())))?;
    parse_skill_manifest(&contents, path)
}

fn parse_skill_manifest(contents: &str, path: &Path) -> Result<SkillManifest, SkillError> {
    let mut in_skill = false;
    let mut values = HashMap::new();
    let mut config = HashMap::new();

    for raw_line in contents.lines() {
        let line = raw_line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if line.starts_with('[') && line.ends_with(']') {
            in_skill = line == "[skill]";
            continue;
        }
        if !in_skill {
            continue;
        }
        let Some((key, value)) = line.split_once('=') else {
            continue;
        };
        let key = key.trim().to_string();
        let value = value.trim().to_string();
        if key.starts_with("config.") {
            config.insert(
                key.trim_start_matches("config.").to_string(),
                unquote(&value),
            );
        } else {
            values.insert(key, value);
        }
    }

    let name = values
        .remove("name")
        .map(|value| unquote(&value))
        .filter(|value| !value.is_empty())
        .ok_or_else(|| SkillError::ParseError(format!("{}: missing skill.name", path.display())))?;
    let version = values
        .remove("version")
        .map(|value| unquote(&value))
        .unwrap_or_else(|| "0.1.0".to_string());
    let description = values
        .remove("description")
        .map(|value| unquote(&value))
        .unwrap_or_default();
    let author = values.remove("author").map(|value| unquote(&value));
    let tags = values
        .remove("tags")
        .map_or_else(Vec::new, |value| parse_array(&value));
    let system_prompt_fragment = values
        .remove("system_prompt_fragment")
        .map(|value| unquote(&value))
        .filter(|value| !value.is_empty());
    let tool_names = values
        .remove("tool_names")
        .map_or_else(Vec::new, |value| parse_array(&value));

    Ok(SkillManifest {
        name,
        version,
        description,
        author,
        tags,
        system_prompt_fragment,
        tool_names,
        config,
    })
}

fn parse_array(value: &str) -> Vec<String> {
    let trimmed = value.trim();
    let trimmed = trimmed
        .strip_prefix('[')
        .and_then(|inner| inner.strip_suffix(']'))
        .unwrap_or(trimmed);
    trimmed
        .split(',')
        .map(str::trim)
        .filter(|part| !part.is_empty())
        .map(unquote)
        .collect()
}

fn unquote(value: &str) -> String {
    value
        .trim()
        .trim_matches('"')
        .trim_matches('\'')
        .to_string()
}

#[cfg(test)]
mod tests {
    use super::{load_skill_manifest, SkillRegistry};
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_dir() -> std::path::PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("time should be after epoch")
            .as_nanos();
        std::env::temp_dir().join(format!("runtime-skills-{nanos}"))
    }

    #[test]
    fn loads_manifest_from_toml_file() {
        let root = temp_dir();
        fs::create_dir_all(&root).expect("temp dir should exist");
        let path = root.join("review.toml");
        fs::write(
            &path,
            r#"[skill]
name = "review"
version = "1.2.3"
description = "Review code"
author = "tests"
tags = ["quality", "safety"]
system_prompt_fragment = "Review carefully"
tool_names = ["grep", "read"]
config.mode = "strict"
"#,
        )
        .expect("manifest write should succeed");

        let manifest = load_skill_manifest(&path).expect("manifest should parse");
        assert_eq!(manifest.name, "review");
        assert_eq!(manifest.version, "1.2.3");
        assert_eq!(manifest.tool_names, vec!["grep", "read"]);
        assert_eq!(
            manifest.config.get("mode").map(String::as_str),
            Some("strict")
        );

        fs::remove_dir_all(root).expect("cleanup temp dir");
    }

    #[test]
    fn registry_loads_manifests_from_search_paths() {
        let root = temp_dir();
        fs::create_dir_all(&root).expect("temp dir should exist");
        fs::write(
            root.join("qa.toml"),
            "[skill]\nname = \"qa\"\ndescription = \"Test app\"\n",
        )
        .expect("manifest write should succeed");
        let mut registry = SkillRegistry::new();
        registry.add_search_path(root.clone());

        let loaded = registry
            .load_from_dirs()
            .expect("registry should load manifests");
        assert_eq!(loaded, 1);
        assert!(registry.get("qa").is_some());

        fs::remove_dir_all(root).expect("cleanup temp dir");
    }
}
