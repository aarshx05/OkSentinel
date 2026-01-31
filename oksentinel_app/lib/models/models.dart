/// API response model
class ApiResponse<T> {
  final bool success;
  final T? data;
  final String? error;
  final String? code;

  ApiResponse({
    required this.success,
    this.data,
    this.error,
    this.code,
  });

  factory ApiResponse.fromJson(
    Map<String, dynamic> json,
    T Function(dynamic)? fromJsonT,
  ) {
    return ApiResponse<T>(
      success: json['success'] ?? false,
      data: fromJsonT != null && json['data'] != null
          ? fromJsonT(json['data'])
          : json['data'] as T?,
      error: json['error'],
      code: json['code'],
    );
  }
}

/// User model
class User {
  final String userId;
  final String username;

  User({
    required this.userId,
    required this.username,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      userId: json['user_id'] ?? '',
      username: json['username'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'user_id': userId,
      'username': username,
    };
  }
}

/// File/Asset model
class AssetFile {
  final String id;
  final String filename;
  final String senderUsername;
  final String assetId;
  final DateTime? createdAt;

  AssetFile({
    required this.id,
    required this.filename,
    required this.senderUsername,
    required this.assetId,
    this.createdAt,
  });

  factory AssetFile.fromJson(Map<String, dynamic> json) {
    return AssetFile(
      id: json['id'] ?? '',
      filename: json['filename'] ?? 'Unknown',
      senderUsername: json['sender_username'] ?? 'Unknown',
      assetId: json['asset_id'] ?? '',
      createdAt: json['created_at'] != null
          ? DateTime.fromMillisecondsSinceEpoch(
              (json['created_at'] * 1000).toInt())
          : null,
    );
  }
}

/// Dashboard data model
class DashboardData {
  final String username;
  final String userId;
  final List<AssetFile> files;
  final int totalFiles;
  final int totalUsers;

  DashboardData({
    required this.username,
    required this.userId,
    required this.files,
    required this.totalFiles,
    required this.totalUsers,
  });

  factory DashboardData.fromJson(Map<String, dynamic> json) {
    return DashboardData(
      username: json['username'] ?? '',
      userId: json['user_id'] ?? '',
      files: (json['files'] as List<dynamic>?)
              ?.map((f) => AssetFile.fromJson(f))
              .toList() ??
          [],
      totalFiles: json['stats']?['total_files'] ?? 0,
      totalUsers: json['stats']?['total_users'] ?? 0,
    );
  }
}

/// File info model
class FileInfo {
  final String filename;
  final String mimetype;
  final int size;
  final int chunkCount;
  final String sender;
  final DateTime? createdAt;
  final DateTime? expiryAt;

  FileInfo({
    required this.filename,
    required this.mimetype,
    required this.size,
    required this.chunkCount,
    required this.sender,
    this.createdAt,
    this.expiryAt,
  });

  factory FileInfo.fromJson(Map<String, dynamic> json) {
    return FileInfo(
      filename: json['filename'] ?? '',
      mimetype: json['mimetype'] ?? 'application/octet-stream',
      size: json['size'] ?? 0,
      chunkCount: json['chunk_count'] ?? 0,
      sender: json['sender'] ?? 'Unknown',
      createdAt: json['created_at'] != null
          ? DateTime.fromMillisecondsSinceEpoch(
              (json['created_at'] * 1000).toInt())
          : null,
      expiryAt: json['expiry_at'] != null
          ? DateTime.fromMillisecondsSinceEpoch(
              (json['expiry_at'] * 1000).toInt())
          : null,
    );
  }

  String get formattedSize {
    if (size < 1024) return '$size B';
    if (size < 1024 * 1024) return '${(size / 1024).toStringAsFixed(1)} KB';
    if (size < 1024 * 1024 * 1024) {
      return '${(size / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(size / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }

  bool get isVideo => mimetype.startsWith('video/');
  bool get isImage => mimetype.startsWith('image/');
  bool get isPdf => mimetype == 'application/pdf';
}
