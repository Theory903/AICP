import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class AicpClient {
  final String baseUrl;

  AicpClient({this.baseUrl = 'http://localhost:8000'});

  Future<List<Capability>> listCapabilities() async {
    final response = await http.get(Uri.parse('$baseUrl/v1/capabilities'));
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return (data['capabilities'] as List)
          .map((c) => Capability.fromJson(c))
          .toList();
    }
    throw Exception('Failed to load capabilities');
  }

  Future<ExecutionResult> execute(
    String capability,
    Map<String, dynamic> arguments,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/v1/execute'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'capability': capability, 'arguments': arguments}),
    );
    if (response.statusCode == 200) {
      return ExecutionResult.fromJson(json.decode(response.body));
    }
    throw Exception('Failed to execute capability');
  }

  Future<List<Approval>> listApprovals() async {
    final response = await http.get(Uri.parse('$baseUrl/v1/approvals'));
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return (data['approvals'] as List)
          .map((a) => Approval.fromJson(a))
          .toList();
    }
    throw Exception('Failed to load approvals');
  }

  Future<void> approve(String approvalId) async {
    await http.post(
      Uri.parse('$baseUrl/v1/approvals/$approvalId/decide'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'decision': 'approve'}),
    );
  }

  Future<void> deny(String approvalId, String reason) async {
    await http.post(
      Uri.parse('$baseUrl/v1/approvals/$approvalId/decide'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'decision': 'deny', 'reason': reason}),
    );
  }
}

class Capability {
  final String name;
  final String description;
  final String kind;

  Capability({
    required this.name,
    required this.description,
    required this.kind,
  });

  factory Capability.fromJson(Map<String, dynamic> json) {
    return Capability(
      name: json['name'],
      description: json['description'] ?? '',
      kind: json['kind'] ?? 'action',
    );
  }
}

class ExecutionResult {
  final String status;
  final dynamic data;
  final String? error;

  ExecutionResult({required this.status, this.data, this.error});

  factory ExecutionResult.fromJson(Map<String, dynamic> json) {
    return ExecutionResult(
      status: json['status'],
      data: json['data'],
      error: json['error'],
    );
  }
}

class Approval {
  final String id;
  final String capability;
  final String status;
  final String? requestedBy;

  Approval({
    required this.id,
    required this.capability,
    required this.status,
    this.requestedBy,
  });

  factory Approval.fromJson(Map<String, dynamic> json) {
    return Approval(
      id: json['id'],
      capability: json['capability'],
      status: json['status'],
      requestedBy: json['requested_by'],
    );
  }
}

void main() {
  runApp(const MammothApp());
}

class MammothApp extends StatelessWidget {
  const MammothApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Mammoth',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _selectedIndex = 0;
  final _aicpClient = AicpClient();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mammoth'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: () {}),
        ],
      ),
      body: [
        CapabilitiesPage(client: _aicpClient),
        const ApprovalsPage(),
        const SettingsPage(),
      ][_selectedIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.grid_view),
            label: 'Capabilities',
          ),
          NavigationDestination(
            icon: Icon(Icons.check_circle_outline),
            label: 'Approvals',
          ),
          NavigationDestination(icon: Icon(Icons.settings), label: 'Settings'),
        ],
      ),
    );
  }
}

class CapabilitiesPage extends StatelessWidget {
  final AicpClient client;

  const CapabilitiesPage({super.key, required this.client});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Capability>>(
      future: client.listCapabilities(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(child: Text('Error: ${snapshot.error}'));
        }
        final capabilities = snapshot.data ?? [];
        return ListView.builder(
          itemCount: capabilities.length,
          itemBuilder: (context, index) {
            final cap = capabilities[index];
            return ListTile(
              leading: const Icon(Icons.flash_on),
              title: Text(cap.name),
              subtitle: Text(cap.description),
              trailing: Chip(label: Text(cap.kind)),
              onTap: () {},
            );
          },
        );
      },
    );
  }
}

class ApprovalsPage extends StatelessWidget {
  const ApprovalsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return const Center(child: Text('No pending approvals'));
  }
}

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        ListTile(
          leading: const Icon(Icons.link),
          title: const Text('AICP Server'),
          subtitle: const Text('http://localhost:8000'),
          onTap: () {},
        ),
        ListTile(
          leading: const Icon(Icons.person),
          title: const Text('Default Model'),
          subtitle: const Text('gpt-4'),
          onTap: () {},
        ),
      ],
    );
  }
}
