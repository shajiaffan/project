import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:audioplayers/audioplayers.dart';
import 'api_service.dart';

class CameraScreen extends StatefulWidget {
  const CameraScreen({Key? key}) : super(key: key);

  @override
  _CameraScreenState createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  File? _imageFile;
  final AudioPlayer _audioPlayer = AudioPlayer();
  final ApiService _apiService = ApiService();

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
      captureImage(); // Automatically open camera
    } else {
      debugPrint("🚨 Camera permission denied!");
    }
  }

  // ✅ Capture Image
  Future<void> captureImage() async {
    try {
      final ImagePicker picker = ImagePicker();
      XFile? pickedFile = await picker.pickImage(source: ImageSource.camera);

      if (pickedFile != null) {
        debugPrint("✅ Image captured: ${pickedFile.path}");

        setState(() {
          _imageFile = File(pickedFile.path);
        });

        await uploadAndPlayAudio(); // Upload image & play audio
      } else {
        debugPrint("🚨 No image captured.");
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

      String audioUrl = await _apiService.uploadImage(_imageFile!.path);
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
      appBar: AppBar(title: const Text("Capture Image")),
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
