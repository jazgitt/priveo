// Generated OpenAPI client contract tests; see generate_contract_cases.py.
import 'package:flutter_test/flutter_test.dart';
import 'package:priveo/core/api/api.g.dart' as wire;
import 'package:priveo/core/network/api_failure.dart';
import 'contract_http.dart';
void main() {
  test('GET /v1/public/health uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.health();
    expect(http.requests.last.path, '/v1/public/health'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.health(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/public/config uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.config();
    expect(http.requests.last.path, '/v1/public/config'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.config(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/auth/support-contact uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.supportContact();
    expect(http.requests.last.path, '/v1/auth/support-contact'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.supportContact(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/auth/legal-links uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.legalLinks();
    expect(http.requests.last.path, '/v1/auth/legal-links'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.legalLinks(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/auth/start uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.start(wire.StartRequest.fromJson((http.examples['StartRequest'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/auth/start'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['StartRequest']);
    http.status=409;
    await expectLater(api.start(wire.StartRequest.fromJson((http.examples['StartRequest'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/auth/code uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.sendCode(wire.CodeRequest.fromJson((http.examples['CodeRequest'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/auth/code'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['CodeRequest']);
    http.status=409;
    await expectLater(api.sendCode(wire.CodeRequest.fromJson((http.examples['CodeRequest'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/auth/code/verify uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.verifyCode(wire.VerifyCodeRequest.fromJson((http.examples['VerifyCodeRequest'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/auth/code/verify'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['VerifyCodeRequest']);
    http.status=409;
    await expectLater(api.verifyCode(wire.VerifyCodeRequest.fromJson((http.examples['VerifyCodeRequest'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/auth/password uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.setPassword(wire.SetPasswordRequest.fromJson((http.examples['SetPasswordRequest'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/auth/password'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['SetPasswordRequest']);
    http.status=409;
    await expectLater(api.setPassword(wire.SetPasswordRequest.fromJson((http.examples['SetPasswordRequest'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/auth/login uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.login(wire.LoginRequest.fromJson((http.examples['LoginRequest'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/auth/login'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['LoginRequest']);
    http.status=409;
    await expectLater(api.login(wire.LoginRequest.fromJson((http.examples['LoginRequest'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/auth/refresh uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.refresh(wire.RefreshRequest.fromJson((http.examples['RefreshRequest'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/auth/refresh'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['RefreshRequest']);
    http.status=409;
    await expectLater(api.refresh(wire.RefreshRequest.fromJson((http.examples['RefreshRequest'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/auth/logout uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.logout();
    expect(http.requests.last.path, '/v1/auth/logout'); expect(http.requests.last.method, 'POST');
    http.status=409;
    await expectLater(api.logout(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/sessions/logout-all uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.logoutAll();
    expect(http.requests.last.path, '/v1/admin/sessions/logout-all'); expect(http.requests.last.method, 'POST');
    http.status=409;
    await expectLater(api.logoutAll(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/customer/profile uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.getProfile();
    expect(http.requests.last.path, '/v1/customer/profile'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.getProfile(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('PATCH /v1/customer/profile uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.patchProfile(wire.AccountProfileEdit.fromJson((http.examples['AccountProfileEdit'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/customer/profile'); expect(http.requests.last.method, 'PATCH');
    expect(http.requests.last.data, http.examples['AccountProfileEdit']);
    http.status=409;
    await expectLater(api.patchProfile(wire.AccountProfileEdit.fromJson((http.examples['AccountProfileEdit'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/customer/profile/email uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.startEmailChange(wire.AccountEmailChange.fromJson((http.examples['AccountEmailChange'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/customer/profile/email'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['AccountEmailChange']);
    http.status=409;
    await expectLater(api.startEmailChange(wire.AccountEmailChange.fromJson((http.examples['AccountEmailChange'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/customer/profile/email/verify uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.verifyEmailChange(wire.AccountEmailCode.fromJson((http.examples['AccountEmailCode'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/customer/profile/email/verify'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['AccountEmailCode']);
    http.status=409;
    await expectLater(api.verifyEmailChange(wire.AccountEmailCode.fromJson((http.examples['AccountEmailCode'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/customer/password uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.changePassword(wire.AccountPasswordChange.fromJson((http.examples['AccountPasswordChange'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/customer/password'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['AccountPasswordChange']);
    http.status=409;
    await expectLater(api.changePassword(wire.AccountPasswordChange.fromJson((http.examples['AccountPasswordChange'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/customer/uploads uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.requestUploadV1CustomerUploadsPost(wire.AccountUploadRequest.fromJson((http.examples['AccountUploadRequest'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/customer/uploads'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['AccountUploadRequest']);
    http.status=409;
    await expectLater(api.requestUploadV1CustomerUploadsPost(wire.AccountUploadRequest.fromJson((http.examples['AccountUploadRequest'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/customer/history/imported uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.myImportedHistory();
    expect(http.requests.last.path, '/v1/customer/history/imported'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.myImportedHistory(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/customer/home uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.customerHome();
    expect(http.requests.last.path, '/v1/customer/home'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.customerHome(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/customer/onboarding uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.onboarding();
    expect(http.requests.last.path, '/v1/customer/onboarding'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.onboarding(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/customer/onboarding/confirm uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.confirmOnboarding(wire.OnboardingAnswers.fromJson((http.examples['OnboardingAnswers'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/customer/onboarding/confirm'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['OnboardingAnswers']);
    http.status=409;
    await expectLater(api.confirmOnboarding(wire.OnboardingAnswers.fromJson((http.examples['OnboardingAnswers'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('PATCH /v1/customer/onboarding/draft uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.saveOnboardingDraft(wire.OnboardingDraft.fromJson((http.examples['OnboardingDraft'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/customer/onboarding/draft'); expect(http.requests.last.method, 'PATCH');
    expect(http.requests.last.data, http.examples['OnboardingDraft']);
    http.status=409;
    await expectLater(api.saveOnboardingDraft(wire.OnboardingDraft.fromJson((http.examples['OnboardingDraft'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/customers uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.createCustomer(wire.CustomerCreate.fromJson((http.examples['CustomerCreate'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/customers'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['CustomerCreate']);
    http.status=409;
    await expectLater(api.createCustomer(wire.CustomerCreate.fromJson((http.examples['CustomerCreate'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/customer-uploads uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.adminUpload(wire.UploadIn.fromJson((http.examples['UploadIn'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/customer-uploads'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['UploadIn']);
    http.status=409;
    await expectLater(api.adminUpload(wire.UploadIn.fromJson((http.examples['UploadIn'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/customer/vehicles uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.customerAddVehicle(wire.VehicleCreate.fromJson((http.examples['VehicleCreate'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/customer/vehicles'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['VehicleCreate']);
    http.status=409;
    await expectLater(api.customerAddVehicle(wire.VehicleCreate.fromJson((http.examples['VehicleCreate'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/customer/onboarding-summary uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.onboardingSummary();
    expect(http.requests.last.path, '/v1/customer/onboarding-summary'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.onboardingSummary(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('PUT /v1/customer/session-device uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.sessionDeviceV1CustomerSessionDevicePut(wire.SessionDevice.fromJson((http.examples['SessionDevice'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/customer/session-device'); expect(http.requests.last.method, 'PUT');
    expect(http.requests.last.data, http.examples['SessionDevice']);
    http.status=409;
    await expectLater(api.sessionDeviceV1CustomerSessionDevicePut(wire.SessionDevice.fromJson((http.examples['SessionDevice'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/scheduling/jobs/swap uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.swapJobs(wire.SwapIn.fromJson((http.examples['SwapIn'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/scheduling/jobs/swap'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['SwapIn']);
    http.status=409;
    await expectLater(api.swapJobs(wire.SwapIn.fromJson((http.examples['SwapIn'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/admin/scheduling/cutoff-requests uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.cutoffRequests();
    expect(http.requests.last.path, '/v1/admin/scheduling/cutoff-requests'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.cutoffRequests(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/admin/operations/reasons uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.reasons();
    expect(http.requests.last.path, '/v1/admin/operations/reasons'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.reasons(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/admin/home uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.adminHome();
    expect(http.requests.last.path, '/v1/admin/home'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.adminHome(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/crew uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.createCrew(wire.NewCrew.fromJson((http.examples['NewCrew'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/crew'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['NewCrew']);
    http.status=409;
    await expectLater(api.createCrew(wire.NewCrew.fromJson((http.examples['NewCrew'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/crew/profile uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.profile();
    expect(http.requests.last.path, '/v1/crew/profile'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.profile(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('PUT /v1/crew/session-device uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.sessionDeviceV1CrewSessionDevicePut(wire.CrewDeviceIn.fromJson((http.examples['CrewDeviceIn'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/crew/session-device'); expect(http.requests.last.method, 'PUT');
    expect(http.requests.last.data, http.examples['CrewDeviceIn']);
    http.status=409;
    await expectLater(api.sessionDeviceV1CrewSessionDevicePut(wire.CrewDeviceIn.fromJson((http.examples['CrewDeviceIn'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/admin/scheduling/automatic-planning uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.automaticSettings();
    expect(http.requests.last.path, '/v1/admin/scheduling/automatic-planning'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.automaticSettings(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('PUT /v1/admin/scheduling/automatic-planning uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.saveAutomaticSettings(wire.AutomaticPlanningSettings.fromJson((http.examples['AutomaticPlanningSettings'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/scheduling/automatic-planning'); expect(http.requests.last.method, 'PUT');
    expect(http.requests.last.data, http.examples['AutomaticPlanningSettings']);
    http.status=409;
    await expectLater(api.saveAutomaticSettings(wire.AutomaticPlanningSettings.fromJson((http.examples['AutomaticPlanningSettings'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/scheduling/run uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.run(wire.RunRequest.fromJson((http.examples['RunRequest'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/scheduling/run'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['RunRequest']);
    http.status=409;
    await expectLater(api.run(wire.RunRequest.fromJson((http.examples['RunRequest'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/scheduling/queue/reorder uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.reorderQueue(wire.QueueReorder.fromJson((http.examples['QueueReorder'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/scheduling/queue/reorder'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['QueueReorder']);
    http.status=409;
    await expectLater(api.reorderQueue(wire.QueueReorder.fromJson((http.examples['QueueReorder'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/scheduling/freeze-due uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.freezeDue();
    expect(http.requests.last.path, '/v1/admin/scheduling/freeze-due'); expect(http.requests.last.method, 'POST');
    http.status=409;
    await expectLater(api.freezeDue(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/customer/notifications/read-all uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.readAll();
    expect(http.requests.last.path, '/v1/customer/notifications/read-all'); expect(http.requests.last.method, 'POST');
    http.status=409;
    await expectLater(api.readAll(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('PUT /v1/customer/devices uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.registerDevice(wire.DeviceBody.fromJson((http.examples['DeviceBody'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/customer/devices'); expect(http.requests.last.method, 'PUT');
    expect(http.requests.last.data, http.examples['DeviceBody']);
    http.status=409;
    await expectLater(api.registerDevice(wire.DeviceBody.fromJson((http.examples['DeviceBody'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/customer/notification-preferences uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.getPreferences();
    expect(http.requests.last.path, '/v1/customer/notification-preferences'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.getPreferences(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('PUT /v1/customer/notification-preferences uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.putPreferences(wire.NotificationPreferencesIn.fromJson((http.examples['NotificationPreferencesIn'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/customer/notification-preferences'); expect(http.requests.last.method, 'PUT');
    expect(http.requests.last.data, http.examples['NotificationPreferencesIn']);
    http.status=409;
    await expectLater(api.putPreferences(wire.NotificationPreferencesIn.fromJson((http.examples['NotificationPreferencesIn'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/crew/notifications/read-all uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.crewReadAll();
    expect(http.requests.last.path, '/v1/crew/notifications/read-all'); expect(http.requests.last.method, 'POST');
    http.status=409;
    await expectLater(api.crewReadAll(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('PUT /v1/crew/devices uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.crewRegisterDevice(wire.DeviceBody.fromJson((http.examples['DeviceBody'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/crew/devices'); expect(http.requests.last.method, 'PUT');
    expect(http.requests.last.data, http.examples['DeviceBody']);
    http.status=409;
    await expectLater(api.crewRegisterDevice(wire.DeviceBody.fromJson((http.examples['DeviceBody'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('PUT /v1/admin/devices uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.adminRegisterDevice(wire.DeviceBody.fromJson((http.examples['DeviceBody'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/devices'); expect(http.requests.last.method, 'PUT');
    expect(http.requests.last.data, http.examples['DeviceBody']);
    http.status=409;
    await expectLater(api.adminRegisterDevice(wire.DeviceBody.fromJson((http.examples['DeviceBody'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/customer/support/contact uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.contact();
    expect(http.requests.last.path, '/v1/customer/support/contact'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.contact(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/customer/support/options uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.options();
    expect(http.requests.last.path, '/v1/customer/support/options'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.options(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/customer/faq uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.faq();
    expect(http.requests.last.path, '/v1/customer/faq'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.faq(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/customer/complaints uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.createComplaint(wire.ComplaintCreate.fromJson((http.examples['ComplaintCreate'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/customer/complaints'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['ComplaintCreate']);
    http.status=409;
    await expectLater(api.createComplaint(wire.ComplaintCreate.fromJson((http.examples['ComplaintCreate'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/customer/feedback uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.giveFeedback(wire.FeedbackCreate.fromJson((http.examples['FeedbackCreate'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/customer/feedback'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['FeedbackCreate']);
    http.status=409;
    await expectLater(api.giveFeedback(wire.FeedbackCreate.fromJson((http.examples['FeedbackCreate'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/customer/checkins uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.submitCheckin(wire.CheckInCreate.fromJson((http.examples['CheckInCreate'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/customer/checkins'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['CheckInCreate']);
    http.status=409;
    await expectLater(api.submitCheckin(wire.CheckInCreate.fromJson((http.examples['CheckInCreate'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/admin/ratings uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.adminRatings();
    expect(http.requests.last.path, '/v1/admin/ratings'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.adminRatings(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/admin/checkins uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.adminCheckins();
    expect(http.requests.last.path, '/v1/admin/checkins'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.adminCheckins(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/support/options uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.adminAddOption(wire.OptionCreate.fromJson((http.examples['OptionCreate'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/support/options'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['OptionCreate']);
    http.status=409;
    await expectLater(api.adminAddOption(wire.OptionCreate.fromJson((http.examples['OptionCreate'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/admin/alerts/email-preferences uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.alertEmailPreferences();
    expect(http.requests.last.path, '/v1/admin/alerts/email-preferences'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.alertEmailPreferences(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('PUT /v1/admin/alerts/email-preferences uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.saveAlertEmailPreferences(wire.AlertEmailPreferences.fromJson((http.examples['AlertEmailPreferences'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/alerts/email-preferences'); expect(http.requests.last.method, 'PUT');
    expect(http.requests.last.data, http.examples['AlertEmailPreferences']);
    http.status=409;
    await expectLater(api.saveAlertEmailPreferences(wire.AlertEmailPreferences.fromJson((http.examples['AlertEmailPreferences'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/alerts/read-all uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.adminAlertsReadAll();
    expect(http.requests.last.path, '/v1/admin/alerts/read-all'); expect(http.requests.last.method, 'POST');
    http.status=409;
    await expectLater(api.adminAlertsReadAll(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/crew/profile/photo uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.photo();
    expect(http.requests.last.path, '/v1/crew/profile/photo'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.photo(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('PUT /v1/crew/profile/photo uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.setPhoto(wire.ProfilePhoto.fromJson((http.examples['ProfilePhoto'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/crew/profile/photo'); expect(http.requests.last.method, 'PUT');
    expect(http.requests.last.data, http.examples['ProfilePhoto']);
    http.status=409;
    await expectLater(api.setPhoto(wire.ProfilePhoto.fromJson((http.examples['ProfilePhoto'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/media/uploads uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.requestUploadV1MediaUploadsPost(wire.UploadRequest.fromJson((http.examples['UploadRequest'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/media/uploads'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['UploadRequest']);
    http.status=409;
    await expectLater(api.requestUploadV1MediaUploadsPost(wire.UploadRequest.fromJson((http.examples['UploadRequest'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/payments uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.createPayment(wire.AdminPaymentIn.fromJson((http.examples['AdminPaymentIn'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/payments'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['AdminPaymentIn']);
    http.status=409;
    await expectLater(api.createPayment(wire.AdminPaymentIn.fromJson((http.examples['AdminPaymentIn'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/customer/addons uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.myAddons();
    expect(http.requests.last.path, '/v1/customer/addons'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.myAddons(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/addons uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.adminRequestAddon(wire.AdminAddonCreate.fromJson((http.examples['AdminAddonCreate'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/addons'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['AdminAddonCreate']);
    http.status=409;
    await expectLater(api.adminRequestAddon(wire.AdminAddonCreate.fromJson((http.examples['AdminAddonCreate'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/web/login uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.webLogin(wire.WebAuthLoginRequest.fromJson((http.examples['WebAuthLoginRequest'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/web/login'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['WebAuthLoginRequest']);
    http.status=409;
    await expectLater(api.webLogin(wire.WebAuthLoginRequest.fromJson((http.examples['WebAuthLoginRequest'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('GET /v1/web/me uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.webMe();
    expect(http.requests.last.path, '/v1/web/me'); expect(http.requests.last.method, 'GET');
    http.status=409;
    await expectLater(api.webMe(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/web/logout uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.webLogout();
    expect(http.requests.last.path, '/v1/web/logout'); expect(http.requests.last.method, 'POST');
    http.status=409;
    await expectLater(api.webLogout(), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/directory/societies uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.createSociety(wire.DirectorySocietyCreate.fromJson((http.examples['DirectorySocietyCreate'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/directory/societies'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['DirectorySocietyCreate']);
    http.status=409;
    await expectLater(api.createSociety(wire.DirectorySocietyCreate.fromJson((http.examples['DirectorySocietyCreate'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/directory/plans uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.createPlan(wire.DirectoryPlanCreate.fromJson((http.examples['DirectoryPlanCreate'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/directory/plans'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['DirectoryPlanCreate']);
    http.status=409;
    await expectLater(api.createPlan(wire.DirectoryPlanCreate.fromJson((http.examples['DirectoryPlanCreate'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/directory/vehicle-catalogue uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.createVehicle(wire.DirectoryVehicleCreate.fromJson((http.examples['DirectoryVehicleCreate'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/directory/vehicle-catalogue'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['DirectoryVehicleCreate']);
    http.status=409;
    await expectLater(api.createVehicle(wire.DirectoryVehicleCreate.fromJson((http.examples['DirectoryVehicleCreate'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/directory/reasons uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.addReason(wire.DirectoryReasonCreate.fromJson((http.examples['DirectoryReasonCreate'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/directory/reasons'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['DirectoryReasonCreate']);
    http.status=409;
    await expectLater(api.addReason(wire.DirectoryReasonCreate.fromJson((http.examples['DirectoryReasonCreate'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
  test('POST /v1/admin/directory/addons uses the published wire contract', () async {
    final http=ContractHttp(); final api=wire.PriveoApi(http.dio());
    await api.createAddon(wire.DirectoryAddonCreate.fromJson((http.examples['DirectoryAddonCreate'] as Map).cast<String,dynamic>()));
    expect(http.requests.last.path, '/v1/admin/directory/addons'); expect(http.requests.last.method, 'POST');
    expect(http.requests.last.data, http.examples['DirectoryAddonCreate']);
    http.status=409;
    await expectLater(api.createAddon(wire.DirectoryAddonCreate.fromJson((http.examples['DirectoryAddonCreate'] as Map).cast<String,dynamic>())), throwsA(isA<ApiFailure>().having((e)=>e.statusCode,'status',409)));
  });
}
