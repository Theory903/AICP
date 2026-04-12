import SwiftUI
import AppKit

@main
struct MammothMenuBarApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @State private var statusItem: NSStatusItem?
    @State private var isConnected = false
    @State private var pendingApprovals = 0
    
    var body: some Scene {
        Settings {
            EmptyView()
        }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem!
    var popover: NSPopover!
    var aicpClient: AicpClient?
    var pollingTimer: Timer?
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        setupStatusItem()
        setupPopover()
        connectToAicp()
        startPolling()
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        pollingTimer?.invalidate()
    }
    
    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        if let button = statusItem.button {
            button.image = NSImage(systemSymbolName: "brain", accessibilityDescription: "Mammoth")
            button.action = #selector(togglePopover)
            button.target = self
        }
    }
    
    private func setupPopover() {
        popover = NSPopover()
        popover.contentSize = NSSize(width: 350, height: 450)
        popover.behavior = .transient
        popover.contentViewController = NSHostingController(rootView: MenuBarView(
            isConnected: .constant(false),
            pendingApprovals: .constant(0)
        ))
    }
    
    private func connectToAicp() {
        aicpClient = AicpClient(baseURL: UserDefaults.standard.string(forKey: "aicpUrl") ?? "http://localhost:8000")
    }
    
    private func startPolling() {
        pollingTimer = Timer.scheduledTimer(withTimeInterval: 10.0, repeats: true) { [weak self] _ in
            self?.checkApprovals()
        }
    }
    
    private func checkApprovals() {
        Task {
            do {
                let approvals = try await aicpClient?.listApprovals()
                DispatchQueue.main.async {
                    self.updateBadge(count: approvals?.count ?? 0)
                }
            } catch {
                print("Failed to check approvals: \(error)")
            }
        }
    }
    
    private func updateBadge(count: Int) {
        if let button = statusItem.button {
            if count > 0 {
                button.image = NSImage(systemSymbolName: "brain.head.profile", accessibilityDescription: "Mammoth - \(count) approvals")
            } else {
                button.image = NSImage(systemSymbolName: "brain", accessibilityDescription: "Mammoth")
            }
        }
    }
    
    @objc private func togglePopover() {
        if popover.isShown {
            popover.performClose(nil)
        } else {
            if let button = statusItem.button {
                popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
            }
        }
    }
}

struct MenuBarView: View {
    @Binding var isConnected: Bool
    @Binding var pendingApprovals: Int
    @State private var prompt: String = ""
    @State private var response: String = ""
    @State private var isLoading: Bool = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "brain")
                    .font(.title2)
                Text("Mammoth")
                    .font(.headline)
                Spacer()
                CircleIndicator(isConnected: isConnected)
            }
            .padding(.bottom, 8)
            
            if pendingApprovals > 0 {
                HStack {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(.orange)
                    Text("\(pendingApprovals) pending approvals")
                        .font(.caption)
                }
                .padding(8)
                .background(Color.orange.opacity(0.1))
                .cornerRadius(8)
            }
            
            VStack(alignment: .leading) {
                Text("Ask Mammoth")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                TextEditor(text: $prompt)
                    .frame(height: 80)
                    .font(.body)
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                    )
            }
            
            Button(action: sendPrompt) {
                HStack {
                    if isLoading {
                        ProgressView()
                            .scaleEffect(0.8)
                    } else {
                        Image(systemName: "paperplane.fill")
                    }
                    Text("Send")
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(prompt.isEmpty || isLoading)
            
            if !response.isEmpty {
                ScrollView {
                    Text(response)
                        .font(.caption)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(height: 100)
            }
            
            Divider()
            
            HStack {
                Button(action: openDashboard) {
                    Image(systemName: "rectangle.3.group")
                }
                .buttonStyle(.borderless)
                .help("Open Dashboard")
                
                Button(action: listCapabilities) {
                    Image(systemName: "list.bullet")
                }
                .buttonStyle(.borderless)
                .help("List Capabilities")
                
                Spacer()
                
                Button(action: openSettings) {
                    Image(systemName: "gear")
                }
                .buttonStyle(.borderless)
                .help("Settings")
            }
        }
        .padding()
    }
    
    private func sendPrompt() {
        isLoading = true
        response = ""
        
        Task {
            try? await Task.sleep(nanoseconds: 500_000_000)
            response = "Mammoth is processing: \(prompt)"
            isLoading = false
        }
    }
    
    private func openDashboard() {
        if let url = URL(string: "http://localhost:8000/console") {
            NSWorkspace.shared.open(url)
        }
    }
    
    private func listCapabilities() {
        // List capabilities
    }
    
    private func openSettings() {
        NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
    }
}

struct CircleIndicator: View {
    let isConnected: Bool
    
    var body: some View {
        Circle()
            .fill(isConnected ? Color.green : Color.red)
            .frame(width: 8, height: 8)
    }
}

class AicpClient {
    let baseURL: String
    
    init(baseURL: String) {
        self.baseURL = baseURL
    }
    
    func listApprovals() async throws -> [Approval]? {
        guard let url = URL(string: "\(baseURL)/v1/approvals") else { return nil }
        let (_, response) = try await URLSession.shared.data(from: url)
        return nil
    }
}

struct Approval: Codable {
    let id: String
    let capability: String
    let status: String
}