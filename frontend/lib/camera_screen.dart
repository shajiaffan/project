import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:audioplayers/audioplayers.dart';
import 'api_service.dart'; // Import the API service

class CameraScreen extends StatefulWidget {
  const CameraScreen({Key? key}) : super(key: key);

  @override
  _CameraScreenState createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  File? _imageFile;
  final AudioPlayer _audioPlayer = AudioPlayer();

  @override
  void initState() {
    super.initState();
    requestPermissions();
  }

  // ✅ Request Permissions
  Future<void> requestPermissions() async {
    Map<Permission, PermissionStatus> statuses = await [
      Permission.camera,
      Permission.storage,
    ].request();

    if (statuses[Permission.camera] == PermissionStatus.granted) {
      captureImage(); // Open camera directly once permission is granted
    } else {
      debugPrint("🚨 Camera permission denied!");
    }
  }

  // ✅ Capture Image Immediately When Screen Loads
  Future<void> captureImage() async {
    try {
      final ImagePicker picker = ImagePicker();
      XFile? pickedFile = await picker.pickImage(source: ImageSource.camera);

      if (pickedFile != null) {
        debugPrint("✅ Image captured at: ${pickedFile.path}");

        setState(() {
          _imageFile = File(pickedFile.path);
        });

        // Upload Image & Get Audio
        await uploadAndPlayAudio();
      } else {
        debugPrint("🚨 No image was captured.");
      }
    } catch (e) {
      debugPrint("❌ Error capturing image: $e");
    }
  }

  // ✅ Upload Image & Play Audio
  Future<void> uploadAndPlayAudio() async {
    if (_imageFile == null) {
      debugPrint("🚨 No image available for upload.");
      return;
    }

    try {
      debugPrint("📤 Uploading image: ${_imageFile!.path}");

      String audioUrl = await ApiService.uploadImage(imageFile: _imageFile!);
      if (audioUrl.isNotEmpty) {
        debugPrint("🔊 Playing audio from: $audioUrl");
        await _audioPlayer.play(UrlSource(audioUrl));
      } else {
        debugPrint("🚨 No audio URL received.");
      }
    } catch (e) {
      debugPrint("❌ Error uploading image or playing audio: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Camera Capture")),
      body: Center(
        child: _imageFile != null
            ? Image.file(_imageFile!)
            : const Text("Capturing image..."),
      ),
    );
  }

  @override
  void dispose() {
    _audioPlayer.dispose();
    super.dispose();
  }
}
