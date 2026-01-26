# OkSentinel

**by OkynusTech**

**Secure Internal Data Sharing Platform**

OkSentinel is an enterprise-grade, zero-leak file sharing system designed for organizations that demand uncompromising security and performance.

## 🛡️ Core Value Proposition

**Zero-Leak Architecture**: Files are encrypted at rest and decrypted progressively in-browser only. No decrypted content ever touches disk storage, preventing data leaks even on compromised endpoints.

**Scalable Performance**: Patent-pending windowed chunk prefetching eliminates buffering during video playback while maintaining strict security boundaries. Streams 500MB+ files seamlessly with minimal memory footprint.

**Enterprise Security**: End-to-end encryption with RSA-4096 + AES-256-CTR, unique nonces per chunk, manifest integrity protection, and automatic expiry enforcement.

---

## 🚀 Key Features

### Security-First Design
- **End-to-End Encryption**: RSA-OAEP-SHA256 for key wrapping, AES-256-CTR for data
- **Zero-Leak Viewing**: Decrypted content exists only in browser memory
- **Integrity Protection**: Cryptographic manifest validation prevents tampering
- **Automatic Expiry**: Time-bound access with strict enforcement

### Performance Innovation
- **Progressive Chunk Streaming**: 4MB chunks enable efficient large file handling
- **Intelligent Prefetching**: Velocity-based pattern detection adapts to user behavior
- **Bounded Memory**: Predictable resource usage regardless of file size
- **Cloud-Ready**: Designed for offline and cloud deployment

### Enterprise Features
- **User Management**: PIN-based authentication with identity isolation
- **Audit Trail**: Comprehensive access logging
- **Expiry Control**: Configurable file lifetimes (hours to weeks)
- **Cross-Platform**: Works on any modern browser

---

## 🎯 Use Cases

- **Confidential Document Sharing**: Legal, financial, medical records
- **Large Media Distribution**: Marketing assets, training videos (up to 500MB)
- **Secure Collaboration**: Cross-team file exchange without public clouds
- **Compliance-Sensitive Data**: GDPR, HIPAA, SOC2 compatible architecture

---

## ⚡ Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd OkSentinel

# Install dependencies
pip install -r requirements.txt

# Run server
python webapp/server.py
```

### First Use

1. Navigate to `http://localhost:5000`
2. Create account (username + PIN)
3. Send encrypted files to other users
4. View files in-browser with zero-leak guarantee

---

## 🏗️ Technology Stack

- **Backend**: Python, Flask
- **Crypto**: RSA-OAEP-SHA256, AES-256-CTR
- **Architecture**: Chunked ByteArray with prefetch
- **Storage**: Portable .ok asset directories

---

## 📄 License

Copyright © 2026. All rights reserved.

This software contains patent-pending technology. Unauthorized reproduction or distribution is prohibited.

---

## 🤝 Support

For enterprise licensing, support, or partnership inquiries, please contact the maintainers.

---

**Built with security, performance, and compliance in mind.**

OkSentinel by OkynusTech - When data integrity matters.
