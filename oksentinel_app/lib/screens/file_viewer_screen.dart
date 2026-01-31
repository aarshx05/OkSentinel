import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:photo_view/photo_view.dart';
import 'package:video_player/video_player.dart';
import '../services/api_service.dart';
import '../models/models.dart';

class FileViewerScreen extends StatefulWidget {
  final AssetFile file;

  const FileViewerScreen({super.key, required this.file});

  @override
  State<FileViewerScreen> createState() => _FileViewerScreenState();
}

class _FileViewerScreenState extends State<FileViewerScreen> {
  final ApiService _apiService = ApiService();
  FileInfo? _fileInfo;
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadFileInfo();
  }

  Future<void> _loadFileInfo() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final response = await _apiService.getFileInfo(widget.file.id);

    if (mounted) {
      setState(() {
        _isLoading = false;
        if (response.success && response.data != null) {
          _fileInfo = response.data;
        } else {
          _errorMessage = response.error ?? 'Failed to load file info';
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.file.filename),
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
                        onPressed: _loadFileInfo,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : _buildViewer(),
    );
  }

  Widget _buildViewer() {
    if (_fileInfo == null) return const SizedBox.shrink();

    if (_fileInfo!.isImage) {
      return _ImageViewer(fileId: widget.file.id, fileInfo: _fileInfo!);
    } else if (_fileInfo!.isVideo) {
      return _VideoViewer(fileId: widget.file.id, fileInfo: _fileInfo!);
    } else if (_fileInfo!.isPdf) {
      return _PdfViewer(fileId: widget.file.id, fileInfo: _fileInfo!);
    } else {
      return _GenericViewer(fileInfo: _fileInfo!);
    }
  }
}

// Image Viewer
class _ImageViewer extends StatelessWidget {
  final String fileId;
  final FileInfo fileInfo;

  const _ImageViewer({required this.fileId, required this.fileInfo});

  @override
  Widget build(BuildContext context) {
    final apiService = ApiService();
    final imageUrl = apiService.getStreamUrl(fileId);

    return Column(
      children: [
        Expanded(
          child: PhotoView(
            imageProvider: NetworkImage(
              imageUrl,
              headers: apiService.streamHeaders,
            ),
            minScale: PhotoViewComputedScale.contained,
            maxScale: PhotoViewComputedScale.covered * 2,
            backgroundDecoration: const BoxDecoration(color: Colors.black),
          ),
        ),
        _buildInfoBar(context),
      ],
    );
  }

  Widget _buildInfoBar(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      color: Theme.of(context).colorScheme.surfaceVariant,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('From: ${fileInfo.sender}',
                    style: Theme.of(context).textTheme.bodyMedium),
                Text(fileInfo.formattedSize,
                    style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ),
          Icon(Icons.lock, color: Theme.of(context).colorScheme.primary),
        ],
      ),
    );
  }
}

// Video Viewer
class _VideoViewer extends StatefulWidget {
  final String fileId;
  final FileInfo fileInfo;

  const _VideoViewer({required this.fileId, required this.fileInfo});

  @override
  State<_VideoViewer> createState() => _VideoViewerState();
}

class _VideoViewerState extends State<_VideoViewer> {
  late VideoPlayerController _controller;
  bool _isInitialized = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _initializeVideo();
  }

  Future<void> _initializeVideo() async {
    try {
      final apiService = ApiService();
      final videoUrl = apiService.getStreamUrl(widget.fileId);

      _controller = VideoPlayerController.networkUrl(
        Uri.parse(videoUrl),
        httpHeaders: apiService.streamHeaders,
      );

      await _controller.initialize();
      
      if (mounted) {
        setState(() {
          _isInitialized = true;
        });
        _controller.play();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'Failed to load video: $e';
        });
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_errorMessage != null) {
      return Center(child: Text(_errorMessage!));
    }

    if (!_isInitialized) {
      return const Center(child: CircularProgressIndicator());
    }

    return Column(
      children: [
        Expanded(
          child: Center(
            child: AspectRatio(
              aspectRatio: _controller.value.aspectRatio,
              child: VideoPlayer(_controller),
            ),
          ),
        ),
        _buildVideoControls(),
      ],
    );
  }

  Widget _buildVideoControls() {
    return Container(
      color: Colors.black87,
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Row(
            children: [
              IconButton(
                icon: Icon(
                  _controller.value.isPlaying ? Icons.pause : Icons.play_arrow,
                  color: Colors.white,
                ),
                onPressed: () {
                  setState(() {
                    _controller.value.isPlaying
                        ? _controller.pause()
                        : _controller.play();
                  });
                },
              ),
              Expanded(
                child: VideoProgressIndicator(
                  _controller,
                  allowScrubbing: true,
                  colors: const VideoProgressColors(
                    playedColor: Colors.blue,
                    bufferedColor: Colors.grey,
                    backgroundColor: Colors.white24,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.fullscreen, color: Colors.white),
                onPressed: () {
                  // Toggle fullscreen (implementation depends on platform)
                },
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'From: ${widget.fileInfo.sender}',
                style: const TextStyle(color: Colors.white70, fontSize: 12),
              ),
              Text(
                widget.fileInfo.formattedSize,
                style: const TextStyle(color: Colors.white70, fontSize: 12),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// PDF Viewer (placeholder - requires external package)
class _PdfViewer extends StatelessWidget {
  final String fileId;
  final FileInfo fileInfo;

  const _PdfViewer({required this.fileId, required this.fileInfo});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.picture_as_pdf, size: 80, color: Colors.red),
            const SizedBox(height: 24),
            Text(
              fileInfo.filename,
              style: Theme.of(context).textTheme.titleLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            Text('PDF Size: ${fileInfo.formattedSize}'),
            const SizedBox(height: 8),
            Text('From: ${fileInfo.sender}'),
            const SizedBox(height: 24),
            const Text(
              'PDF viewing in-app is coming soon!',
              style: TextStyle(color: Colors.grey),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () {
                // Open in external app
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('External PDF viewing coming soon'),
                  ),
                );
              },
              icon: const Icon(Icons.open_in_new),
              label: const Text('Open in External Viewer'),
            ),
          ],
        ),
      ),
    );
  }
}

// Generic file viewer
class _GenericViewer extends StatelessWidget {
  final FileInfo fileInfo;

  const _GenericViewer({required this.fileInfo});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.insert_drive_file, size: 80, color: Colors.blue),
            const SizedBox(height: 24),
            Text(
              fileInfo.filename,
              style: Theme.of(context).textTheme.titleLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    _InfoRow('Type', fileInfo.mimetype),
                    _InfoRow('Size', fileInfo.formattedSize),
                    _InfoRow('From', fileInfo.sender),
                    _InfoRow('Chunks', fileInfo.chunkCount.toString()),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'This file type cannot be viewed in-app',
              style: TextStyle(color: Colors.grey),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
          Text(value),
        ],
      ),
    );
  }
}
