/// Plain shapes for the scheduling read models (`GET /v1/customer/next-service`
/// and `GET /v1/crew/day`). They are not generated from the contract yet:
/// replace them with `api.g.dart` once the contract carries these endpoints.
library;

/// The next open job on a customer's vehicles. Times are "HH:MM".
class NextServiceJob {
  const NextServiceJob({
    required this.jobId,
    required this.visitId,
    required this.vehicleId,
    required this.registration,
    required this.vehicle,
    required this.date,
    required this.service,
    required this.status,
    this.startTime,
    this.endTime,
    this.crewName,
    this.finishBy,
  });

  final String jobId;
  final String visitId;
  final String vehicleId;
  final String registration;
  final String vehicle;
  final DateTime date;
  final String service;
  final String status;
  final String? startTime;
  final String? endTime;
  final String? crewName;
  final String? finishBy;

  factory NextServiceJob.fromJson(Map<String, dynamic> json) => NextServiceJob(
        jobId: json['job_id'] as String,
        visitId: json['visit_id'] as String,
        vehicleId: json['vehicle_id'] as String,
        registration: json['registration'] as String,
        vehicle: json['vehicle'] as String,
        date: DateTime.parse(json['date'] as String),
        service: json['service'] as String,
        status: json['status'] as String,
        startTime: json['start_time'] as String?,
        endTime: json['end_time'] as String?,
        crewName: json['crew_name'] as String?,
        finishBy: json['finish_by'] as String?,
      );
}

/// The response of `GET /v1/customer/next-service`: `job` is null when
/// nothing is assigned yet.
NextServiceJob? nextServiceFromJson(Map<String, dynamic> json) {
  final job = json['job'];
  return job == null ? null : NextServiceJob.fromJson(job as Map<String, dynamic>);
}

/// One card in the crew's day. It never carries a customer name or mobile.
class CrewDayJob {
  const CrewDayJob({
    required this.id,
    required this.visitId,
    required this.vehicleId,
    required this.registration,
    required this.make,
    required this.model,
    required this.category,
    required this.parkingBasement,
    required this.parkingNumber,
    required this.society,
    required this.service,
    required this.status,
    this.startTime,
    this.endTime,
    this.finishBy,
  });

  final String id;
  final String visitId;
  final String vehicleId;
  final String registration;
  final String make;
  final String model;
  final String category;
  final String parkingBasement;
  final String parkingNumber;
  final String society;
  final String service;
  final String status;
  final String? startTime;
  final String? endTime;
  final String? finishBy;

  factory CrewDayJob.fromJson(Map<String, dynamic> json) => CrewDayJob(
        id: json['id'] as String,
        visitId: json['visit_id'] as String,
        vehicleId: json['vehicle_id'] as String,
        registration: json['registration'] as String,
        make: json['make'] as String,
        model: json['model'] as String,
        category: json['category'] as String,
        parkingBasement: json['parking_basement'] as String,
        parkingNumber: json['parking_number'] as String,
        society: json['society'] as String,
        service: json['service'] as String,
        status: json['status'] as String,
        startTime: json['start_time'] as String?,
        endTime: json['end_time'] as String?,
        finishBy: json['finish_by'] as String?,
      );
}

class CrewDay {
  const CrewDay({
    required this.date,
    required this.society,
    required this.total,
    required this.done,
    required this.left,
    required this.jobs,
  });

  final DateTime date;
  final String society;
  final int total;
  final int done;
  final int left;
  final List<CrewDayJob> jobs;

  factory CrewDay.fromJson(Map<String, dynamic> json) => CrewDay(
        date: DateTime.parse(json['date'] as String),
        society: json['society'] as String,
        total: json['total'] as int,
        done: json['done'] as int,
        left: json['left'] as int,
        jobs: [
          for (final j in json['jobs'] as List<dynamic>)
            CrewDayJob.fromJson(j as Map<String, dynamic>),
        ],
      );
}
