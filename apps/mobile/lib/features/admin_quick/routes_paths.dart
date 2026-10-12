/// Paths of the admin quick-action screens. They sit under `/admin/`, so the
/// role redirect lets them through.
class AdminQuickPaths {
  static const operations = '/admin/operations';
  static const customers = '/admin/customers';
  static const customerPattern = '/admin/customers/:id';
  static String customer(String id) => '/admin/customers/$id';
  static const crew = '/admin/crew';
  static const addons = '/admin/addons';
  static const checkins = '/admin/checkins';
  static const complaints = '/admin/complaints';
  static const complaintPattern = '/admin/complaints/:id';
  static String complaint(String id) => '/admin/complaints/$id';
  static const feedback = '/admin/feedback';
  static const needsScheduling = '/admin/needs-scheduling';
  static const day = '/admin/day';
  static const capacity = '/admin/capacity';
}
