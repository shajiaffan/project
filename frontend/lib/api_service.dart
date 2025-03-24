import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  final String baseUrl = 'http://13.61.227.55:8000';

  Future<String> uploadImage(String imagePath) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/upload'));
      request.files.add(await http.MultipartFile.fromPath('file', imagePath));
      var response = await request.send();

      if (response.statusCode == 200) {
        final responseData = await response.stream.bytesToString();
        return responseData;
      } else {
        throw Exception('Failed to upload image');
      }
    } catch (e) {
      throw Exception('Error uploading image: $e');
    }
  }

  Future<void> playAudio(String audioUrl) async {
    // Assuming your API returns an audio URL
    try {
      print("Playing audio from: $audioUrl");
      // Implement audio player logic using audioplayers or just_audio
    } catch (e) {
      print('Error playing audio: $e');
    }
  }
}
