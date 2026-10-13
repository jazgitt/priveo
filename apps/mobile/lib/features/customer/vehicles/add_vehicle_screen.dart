import 'package:dio/dio.dart';
import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/providers.dart';
import '../../../core/network/api_failure.dart';
import '../../../core/ui/media_image.dart';
import '../../../core/ui/widgets.dart';
import '../../../l10n/app_localizations.dart';
import '../../changes_money/routes.dart' show payPath;
import '../account/photo_widgets.dart' show captureAndUpload;
import '../data/customer_reads_repository.dart';
import '../home/customer_home_data.dart';

class VehicleDirectory {
  const VehicleDirectory(this.societies, this.catalogue, this.plans);
  final List<Map<String, dynamic>> societies, catalogue, plans;
}

final vehicleDirectoryProvider = FutureProvider.autoDispose<VehicleDirectory>((
  ref,
) async {
  final dio = ref.watch(dioProvider);
  final results = await Future.wait([
    dio.get<List<dynamic>>('/v1/customer/directory/societies'),
    dio.get<List<dynamic>>('/v1/customer/directory/vehicle-catalogue'),
    dio.get<List<dynamic>>('/v1/customer/directory/plans'),
  ]);
  List<Map<String, dynamic>> rows(int n) =>
      results[n].data!.cast<Map<String, dynamic>>();
  return VehicleDirectory(rows(0), rows(1), rows(2));
});

class AddVehicleScreen extends ConsumerStatefulWidget {
  const AddVehicleScreen({super.key});
  @override
  ConsumerState<AddVehicleScreen> createState() => _State();
}

class _State extends ConsumerState<AddVehicleScreen> {
  final _registration = TextEditingController(),
      _parking = TextEditingController();
  int step = 0;
  String societyId = '', make = '', model = '', catalogueId = '', basement = '';
  String planId = '', cutoff = '09:00', interior = '', search = '';
  String? photoId, photoUrl, rcId, failure;
  Map<String, dynamic>? created;
  bool busy = false;
  @override
  void dispose() {
    _registration.dispose();
    _parking.dispose();
    super.dispose();
  }

  Map<String, dynamic>? selected(List<Map<String, dynamic>> list, String id) =>
      list.where((r) => r['id'] == id).firstOrNull;

  Future<void> photo() async {
    setState(() {
      failure = null;
    });
    try {
      final file = await captureAndUpload(
        context,
        ref,
        purpose: 'vehicle',
        onSending: () {
          if (mounted) setState(() => busy = true);
        },
      );
      if (file != null && mounted) {
        setState(() {
          photoId = file.id;
          photoUrl = file.url;
        });
      }
    } catch (e) {
      if (mounted) setState(() => failure = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> rc() async {
    final l = AppLocalizations.of(context);
    setState(() {
      busy = true;
      failure = null;
    });
    try {
      final file = await openFile(
        acceptedTypeGroups: [
          const XTypeGroup(
            label: 'RC',
            extensions: ['jpg', 'jpeg', 'png', 'pdf'],
            mimeTypes: ['image/jpeg', 'image/png', 'application/pdf'],
            uniformTypeIdentifiers: [
              'public.jpeg',
              'public.png',
              'com.adobe.pdf',
            ],
          ),
        ],
      );
      if (file == null) return;
      final bytes = await file.readAsBytes();
      if (bytes.isEmpty || bytes.length > 5 * 1024 * 1024) {
        throw l.addVehicleRcLimit;
      }
      final extension = file.name.split('.').last.toLowerCase();
      final type = extension == 'pdf'
          ? 'application/pdf'
          : extension == 'png'
          ? 'image/png'
          : 'image/jpeg';
      final dio = ref.read(dioProvider);
      final ticket = (await dio.post<Map<String, dynamic>>(
        '/v1/customer/uploads',
        data: {
          'purpose': 'rc',
          'content_type': type,
          'size_bytes': bytes.length,
        },
      )).data!;
      // Signed URLs carry authorization; never attach the API's bearer token.
      await Dio().request<void>(
        Uri.parse(
          dio.options.baseUrl,
        ).resolve(ticket['upload_url'] as String).toString(),
        data: Stream.value(bytes),
        options: Options(
          method: ticket['method'] as String,
          headers: {
            ...(ticket['headers'] as Map).cast<String, dynamic>(),
            'Content-Length': bytes.length,
          },
        ),
      );
      await dio.post('/v1/customer/uploads/${ticket['id']}/confirm');
      if (mounted) setState(() => rcId = ticket['id'] as String);
    } on DioException catch (e) {
      if (mounted) setState(() => failure = ApiFailure.fromDio(e).message);
    } catch (e) {
      if (mounted) setState(() => failure = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  bool valid(Map<String, dynamic>? plan) => switch (step) {
    0 => societyId.isNotEmpty,
    1 =>
      catalogueId.isNotEmpty &&
          RegExp(
            r'^(?:[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{4}|\d{2}BH\d{4}[A-Z]{1,2})$',
          ).hasMatch(_registration.text.replaceAll(' ', '').toUpperCase()) &&
          photoId != null,
    2 => basement.isNotEmpty && RegExp(r'^\d{1,5}$').hasMatch(_parking.text),
    3 => planId.isNotEmpty,
    4 => plan?['includes_interior'] != true || interior.isNotEmpty,
    _ => true,
  };

  Future<void> save() async {
    setState(() {
      busy = true;
      failure = null;
    });
    try {
      final directory = ref.read(vehicleDirectoryProvider).requireValue;
      final plan = selected(directory.plans, planId)!;
      created ??=
          (await ref
                  .read(dioProvider)
                  .post<Map<String, dynamic>>(
                    '/v1/customer/vehicles',
                    data: {
                      'society_id': societyId,
                      'catalogue_id': catalogueId,
                      'registration': _registration.text,
                      'parking_basement': basement,
                      'parking_number': _parking.text,
                      'plan_id': planId,
                      'cutoff_time': cutoff,
                      'interior_day': plan['includes_interior'] == true
                          ? interior
                          : null,
                      'photo_upload_id': photoId,
                      'rc_upload_id': rcId,
                    },
                  ))
              .data!;
      ref.invalidate(vehiclesProvider);
      ref.invalidate(customerHomeProvider);
      if (mounted) {
        final router = GoRouter.of(context);
        Navigator.of(context).pop();
        router.push(payPath(created!['payment_id'] as String));
      }
    } on DioException catch (e) {
      if (mounted) setState(() => failure = ApiFailure.fromDio(e).message);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Widget select(
    String label,
    String value,
    List<(String, String)> values,
    void Function(String) change,
  ) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: DropdownButtonFormField<String>(
      key: ValueKey('$label:$value'),
      initialValue: value.isEmpty ? null : value,
      isExpanded: true,
      decoration: InputDecoration(labelText: label),
      items: values
          .map((v) => DropdownMenuItem(value: v.$1, child: Text(v.$2)))
          .toList(),
      onChanged: busy ? null : (v) => setState(() => change(v ?? '')),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final directory = ref.watch(vehicleDirectoryProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l.addVehicleTitle)),
      body: directory.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorView(
          message: e.toString(),
          onRetry: () => ref.invalidate(vehicleDirectoryProvider),
        ),
        data: (data) {
          final society = selected(data.societies, societyId),
              entry = selected(data.catalogue, catalogueId),
              plan = selected(data.plans, planId);
          final stages = [
            l.addVehicleSociety,
            l.addVehicleCar,
            l.addVehicleParking,
            l.addVehiclePlan,
            l.addVehiclePreferences,
            l.addVehicleReview,
          ];
          final days = [
            'Monday',
            'Tuesday',
            'Wednesday',
            'Thursday',
            'Friday',
            'Saturday',
            'Sunday',
          ];
          return Column(
            children: [
              LinearProgressIndicator(value: (step + 1) / 6),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.all(20),
                  children: [
                    Text(
                      '${step + 1}/6 · ${stages[step]}',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    if (failure != null)
                      Text(
                        failure!,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    if (step == 0) ...[
                      TextField(
                        decoration: InputDecoration(
                          labelText: l.addVehicleSearch,
                        ),
                        onChanged: (v) => setState(() => search = v),
                      ),
                      if (data.societies.isEmpty) Text(l.addVehicleNoSocieties),
                      for (final s in data.societies.where(
                        (s) => '${s['name']} ${s['sector']} ${s['city']}'
                            .toLowerCase()
                            .contains(search.toLowerCase()),
                      ))
                        ListTile(
                          title: Text(s['name'] as String),
                          subtitle: Text(
                            '${s['sector']} ${s['city']} · ${s['cars_serviced']}',
                          ),
                          trailing: Icon(
                            societyId == s['id']
                                ? Icons.radio_button_checked
                                : Icons.radio_button_unchecked,
                          ),
                          onTap: () => setState(() {
                            societyId = s['id'] as String;
                            basement = '';
                          }),
                        ),
                      Text(l.addVehicleSocietyFixed),
                    ],
                    if (step == 1) ...[
                      select(
                        l.addVehicleMake,
                        make,
                        data.catalogue
                            .map((e) => e['make'] as String)
                            .toSet()
                            .map((m) => (m, m))
                            .toList(),
                        (v) {
                          make = v;
                          model = '';
                          catalogueId = '';
                        },
                      ),
                      select(
                        l.addVehicleModel,
                        model,
                        data.catalogue
                            .where((e) => e['make'] == make)
                            .map((e) => e['model'] as String)
                            .toSet()
                            .map((m) => (m, m))
                            .toList(),
                        (v) {
                          model = v;
                          catalogueId = '';
                        },
                      ),
                      select(
                        l.addVehicleVariant,
                        catalogueId,
                        data.catalogue
                            .where(
                              (e) => e['make'] == make && e['model'] == model,
                            )
                            .map(
                              (e) => (
                                e['id'] as String,
                                e['variant'] == ''
                                    ? l.addVehicleStandard
                                    : e['variant'] as String,
                              ),
                            )
                            .toList(),
                        (v) => catalogueId = v,
                      ),
                      if (entry != null)
                        Text('${entry['category']} · ${l.addVehicleAuto}'),
                      TextField(
                        controller: _registration,
                        inputFormatters: [TextInputFormatter.withFunction((old, value) =>
                            value.copyWith(text: value.text.toUpperCase()))],
                        textCapitalization: TextCapitalization.characters,
                        decoration: InputDecoration(
                          labelText: l.addVehicleRegistration,
                          hintText: 'HR26EC4321',
                        ),
                        onChanged: (_) => setState(() {}),
                      ),
                      if (photoUrl != null)
                        SizedBox(height: 140, child: MediaImage(photoUrl!)),
                      TextButton(
                        onPressed: busy ? null : photo,
                        child: Text(
                          photoId == null
                              ? l.addVehiclePhoto
                              : l.addVehicleReplacePhoto,
                        ),
                      ),
                      TextButton(
                        onPressed: busy ? null : rc,
                        child: Text(
                          rcId == null
                              ? l.addVehicleRc
                              : l.addVehicleRcUploaded,
                        ),
                      ),
                    ],
                    if (step == 2) ...[
                      select(
                        l.addVehicleBasement,
                        basement,
                        (society?['parking_basements'] as List? ?? [])
                            .map((b) => (b as String, b))
                            .toList(),
                        (v) => basement = v,
                      ),
                      TextField(
                        controller: _parking,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText: l.addVehicleParkingNumber,
                        ),
                        onChanged: (_) => setState(() {}),
                      ),
                      Text('$basement · ${_parking.text}'),
                    ],
                    if (step == 3) ...[
                      for (final p in data.plans)
                        Card(
                          child: ListTile(
                            title: Text(
                              '${p['name']} · ₹${p['monthly_price_rupees']}/month',
                            ),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (p['list_price_rupees'] != null)
                                  Text(
                                    '₹${p['list_price_rupees']}',
                                    style: const TextStyle(
                                      decoration: TextDecoration.lineThrough,
                                    ),
                                  ),
                                Text('${p['badge']} · ${l.addVehicleCancel}'),
                                for (final i in p['inclusions'] as List)
                                  Text('• $i'),
                              ],
                            ),
                            trailing: Icon(
                              planId == p['id']
                                  ? Icons.check_circle
                                  : Icons.circle_outlined,
                            ),
                            onTap: () => setState(() {
                              planId = p['id'] as String;
                              interior = '';
                            }),
                          ),
                        ),
                    ],
                    if (step == 4) ...[
                      select(
                        l.addVehicleCutoff,
                        cutoff,
                        List.generate(48, (i) {
                          final t =
                              '${(i ~/ 2).toString().padLeft(2, '0')}:${i.isEven ? '00' : '30'}';
                          return (t, t);
                        }),
                        (v) => cutoff = v,
                      ),
                      Text(l.addVehicleSlotNote),
                      if (plan?['includes_interior'] == true)
                        select(
                          l.addVehicleInterior,
                          interior,
                          days.map((d) => (d, d)).toList(),
                          (v) => interior = v,
                        ),
                    ],
                    if (step == 5) ...[
                      Text(
                        '${society?['name']} · ${entry?['make']} ${entry?['model']} ${entry?['variant']}',
                      ),
                      Text(_registration.text.toUpperCase()),
                      Text('$basement · ${_parking.text}'),
                      Text(
                        '$cutoff${interior.isNotEmpty ? ' · $interior' : ''}',
                      ),
                      Text(
                        '${plan?['name']} · ₹${plan?['monthly_price_rupees']}',
                      ),
                      Text(l.addVehicleTotal),
                      Text(l.addVehicleStartNote),
                    ],
                  ],
                ),
              ),
              SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      if (step > 0)
                        TextButton(
                          onPressed: busy ? null : () => setState(() => step--),
                          child: Text(l.addVehicleBack),
                        ),
                      Expanded(
                        child: PrimaryButton(
                          label: step == 5
                              ? l.addVehicleConfirm
                              : l.continueButton,
                          busy: busy,
                          onPressed: () {
                            if (!valid(plan)) {
                              setState(() => failure = l.addVehicleRequired);
                              return;
                            }
                            if (step == 5) {
                              save();
                            } else {
                              setState(() {
                                step++;
                                failure = null;
                              });
                            }
                          },
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
