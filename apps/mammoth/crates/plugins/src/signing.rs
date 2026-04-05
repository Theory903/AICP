use ed25519_dalek::{Signer, SigningKey, Verifier, VerifyingKey};

pub struct PluginSigner {
    key: SigningKey,
}

impl PluginSigner {
    #[must_use]
    pub fn from_seed(seed: &[u8; 32]) -> Self {
        Self {
            key: SigningKey::from_bytes(seed),
        }
    }

    #[must_use]
    pub fn sign(&self, data: &[u8]) -> [u8; 64] {
        self.key.sign(data).to_bytes()
    }

    #[must_use]
    pub fn verifying_key_bytes(&self) -> [u8; 32] {
        self.key.verifying_key().to_bytes()
    }
}

#[derive(Debug)]
pub struct VerificationError(String);

impl std::fmt::Display for VerificationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "signature verification failed: {}", self.0)
    }
}

pub struct PluginVerifier {
    key: VerifyingKey,
}

impl PluginVerifier {
    pub fn new(pub_key_bytes: &[u8; 32]) -> Result<Self, VerificationError> {
        VerifyingKey::from_bytes(pub_key_bytes)
            .map(|key| Self { key })
            .map_err(|e| VerificationError(e.to_string()))
    }

    pub fn verify(&self, data: &[u8], signature_bytes: &[u8; 64]) -> Result<(), VerificationError> {
        let sig = ed25519_dalek::Signature::from_bytes(signature_bytes);
        self.key
            .verify(data, &sig)
            .map_err(|e| VerificationError(e.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip_sign_verify() {
        let seed = [0u8; 32];
        let signer = PluginSigner::from_seed(&seed);
        let pub_key = signer.verifying_key_bytes();
        let data = b"plugin-binary-hash-abc123";
        let sig = signer.sign(data);
        let verifier = PluginVerifier::new(&pub_key).unwrap();
        assert!(verifier.verify(data, &sig).is_ok());
    }

    #[test]
    fn tampered_data_fails_verification() {
        let seed = [1u8; 32];
        let signer = PluginSigner::from_seed(&seed);
        let pub_key = signer.verifying_key_bytes();
        let sig = signer.sign(b"original");
        let verifier = PluginVerifier::new(&pub_key).unwrap();
        assert!(verifier.verify(b"tampered", &sig).is_err());
    }

    #[test]
    fn wrong_key_fails_verification() {
        let seed_a = [2u8; 32];
        let seed_b = [3u8; 32];
        let signer_a = PluginSigner::from_seed(&seed_a);
        let signer_b = PluginSigner::from_seed(&seed_b);
        let pub_key_b = signer_b.verifying_key_bytes();
        let sig = signer_a.sign(b"data");
        let verifier = PluginVerifier::new(&pub_key_b).unwrap();
        assert!(verifier.verify(b"data", &sig).is_err());
    }
}
