import 'dart:io';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;

class ApiService {
  static Future<String> uploadImage({File? imageFile, Uint8List? webImageBytes}) async {
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('http://192.168.1.13:8000/generate_caption'), // Ensure correct API URL
    );

    if (kIsWeb && webImageBytes != null) {
      request.files.add(
        http.MultipartFile.fromBytes(
          'image_file',
          webImageBytes,
          filename: 'image.jpg',
        ),
      );
    } else if (imageFile != null) {
      request.files.add(
        await http.MultipartFile.fromPath('image_file', imageFile.path),
      );
    }

    var response = await request.send();
    if (response.statusCode == 200) {
      var responseBody = await response.stream.bytesToString();
      var jsonData = json.decode(responseBody);
      return jsonData['audio_url']; // Ensure API returns a valid 'audio_url'
    } else {
      return "";
    }
  }
}
