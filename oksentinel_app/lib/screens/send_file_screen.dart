import 'dart:io';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../services/api_service.dart';
import '../models/models.dart';

class SendFileScreen extends StatefulWidget {
  const SendFileScreen({super.key});

  @override
  State<SendFileScreen> createState() => _SendFileScreenState();
}

class _SendFileScreenState extends State<SendFileScreen> {
  final ApiService _apiService = ApiService();
  
  File? _selectedFile;
  String? _selectedRecipientId;
  double _expiryHours = 24;
  bool _isLoading = true;
  bool _isSending = false;
  List<User> _users = [];
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadUsers();
  }

  Future<void> _loadUsers() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final response = await _apiService.getUsers();

    if (mounted) {
      setState(() {
        _isLoading = false;
        if (response.success && response.data != null) {
          _users = response.data!;
        } else {
          _errorMessage = response.error ?? 'Failed to load users';
        }
      });
    }
  }

  Future<void> _pickFile() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.any,
        allowMultiple: false,
      );

      if (result != null && result.files.single.path != null) {
        setState(() {
          _selectedFile = File(result.files.single.path!);
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error picking file: $e')),
        );
      }
    }
  }

  Future<void> _sendFile() async {
    if (_selectedFile == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a file')),
      );
      return;
    }

    if (_selectedRecipientId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a recipient')),
      );
      return;
    }

    setState(() {
      _isSending = true;
    });

    final response = await _apiService.sendFile(
      _selectedFile!,
      _selectedRecipientId!,
      _expiryHours,
      null,
    );

    if (mounted) {
      setState(() {
        _isSending = false;
      });

      if (response.success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(response.data?['message'] ?? 'File sent successfully!'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.of(context).pop(true); // Return true to indicate success
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(response.error ?? 'Failed to send file'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Send File'),
        elevation: 0,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error_outline,
                          size: 64, color: Colors.red),
                      const SizedBox(height: 16),
                      Text(_errorMessage!),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _loadUsers,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    // File selector
                    Card(
                      child: InkWell(
                        onTap: _isSending ? null : _pickFile,
                        borderRadius: BorderRadius.circular(12),
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Column(
                            children: [
                              Icon(
                                _selectedFile == null
                                    ? Icons.upload_file
                                    : Icons.check_circle,
                                size: 64,
                                color: _selectedFile == null
                                    ? Theme.of(context).colorScheme.primary
                                    : Colors.green,
                              ),
                              const SizedBox(height: 16),
                              Text(
                                _selectedFile == null
                                    ? 'Tap to select file'
                                    : _selectedFile!.path.split(Platform.pathSeparator).last,
                                style: Theme.of(context).textTheme.titleMedium,
                                textAlign: TextAlign.center,
                              ),
                              if (_selectedFile != null) ...[
                                const SizedBox(height: 8),
                                FutureBuilder<int>(
                                  future: _selectedFile!.length(),
                                  builder: (context, snapshot) {
                                    if (snapshot.hasData) {
                                      final size = snapshot.data!;
                                      final sizeStr = size < 1024
                                          ? '$size B'
                                          : size < 1024 * 1024
                                              ? '${(size / 1024).toStringAsFixed(1)} KB'
                                              : '${(size / (1024 * 1024)).toStringAsFixed(1)} MB';
                                      return Text(
                                        sizeStr,
                                        style: Theme.of(context).textTheme.bodySmall,
                                      );
                                    }
                                    return const SizedBox.shrink();
                                  },
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    
                    // Recipient selector
                    Text(
                      'Select Recipient',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 12),
                    if (_users.isEmpty)
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Text(
                            'No other users available',
                            style: TextStyle(color: Colors.grey[600]),
                            textAlign: TextAlign.center,
                          ),
                        ),
                      )
                    else
                      ...(_users.map((user) => RadioListTile<String>(
                            title: Text(user.username),
                            value: user.userId,
                            groupValue: _selectedRecipientId,
                            onChanged: _isSending
                                ? null
                                : (value) {
                                    setState(() {
                                      _selectedRecipientId = value;
                                    });
                                  },
                          ))),
                    const SizedBox(height: 24),
                    
                    // Expiry selector
                    Text(
                      'Expiration Time',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(height: 12),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          children: [
                            Text(
                              '${_expiryHours.toInt()} hours',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            Slider(
                              value: _expiryHours,
                              min: 1,
                              max: 168, // 1 week
                              divisions: 167,
                              label: '${_expiryHours.toInt()}h',
                              onChanged: _isSending
                                  ? null
                                  : (value) {
                                      setState(() {
                                        _expiryHours = value;
                                      });
                                    },
                            ),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text('1h',
                                    style: Theme.of(context).textTheme.bodySmall),
                                Text('1 week',
                                    style: Theme.of(context).textTheme.bodySmall),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 32),
                    
                    // Send button
                    ElevatedButton(
                      onPressed: _isSending ? null : _sendFile,
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                      child: _isSending
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.send),
                                SizedBox(width: 8),
                                Text('Send Encrypted File',
                                    style: TextStyle(fontSize: 16)),
                              ],
                            ),
                    ),
                  ],
                ),
    );
  }
}
