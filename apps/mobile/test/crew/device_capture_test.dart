import 'dart:convert';
import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mocktail/mocktail.dart';
import 'package:priveo/features/crew/capture/media_capture.dart';

class Picker extends Mock implements ImagePicker {}
void main(){
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(()=>registerFallbackValue(ImageSource.camera));
  test('photo capture uses compression settings, camera/gallery sources and cancellation',()async{
    final picker=Picker();final file=File('test/crew/capture-unit.jpg');await file.writeAsBytes([1,2,3]);
    try{
      when(()=>picker.pickImage(source:any(named:'source'),maxWidth:2048,maxHeight:2048,imageQuality:80)).thenAnswer((_)async=>XFile(file.path));
      final capture=DeviceMediaCapture(picker);final photo=await capture.photo(camera:true);expect(photo!.sizeBytes,3);expect(photo.contentType,'image/jpeg');expect(photo.video,isFalse);
      await capture.photo(camera:false);verify(()=>picker.pickImage(source:ImageSource.gallery,maxWidth:2048,maxHeight:2048,imageQuality:80)).called(1);
      when(()=>picker.pickImage(source:any(named:'source'),maxWidth:2048,maxHeight:2048,imageQuality:80)).thenAnswer((_)async=>null);expect(await capture.photo(camera:true),isNull);
    }finally{await file.delete();}
  });
  test('video compression retains audio, keeps the original and handles cancellation',()async{
    final picker=Picker();final file=File('test/crew/capture-unit.mp4');await file.writeAsBytes([1,2,3,4]);
    final calls=<MethodCall>[];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(const MethodChannel('video_compress'),(call)async{calls.add(call);return jsonEncode({'path':file.path,'filesize':4,'duration':1000});});
    try{
      when(()=>picker.pickVideo(source:any(named:'source'),maxDuration:const Duration(minutes:2))).thenAnswer((_)async=>XFile(file.path));
      final capture=DeviceMediaCapture(picker);final video=await capture.video(camera:false);expect(video!.video,isTrue);expect(video.contentType,'video/mp4');expect(video.sizeBytes,4);
      expect(calls.single.arguments,containsPair('deleteOrigin',false));expect(calls.single.arguments,containsPair('includeAudio',true));
      when(()=>picker.pickVideo(source:any(named:'source'),maxDuration:const Duration(minutes:2))).thenAnswer((_)async=>null);expect(await capture.video(camera:true),isNull);
    }finally{TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(const MethodChannel('video_compress'),null);await file.delete();}
  });
}
