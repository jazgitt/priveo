/// The keys of the admin's feature flags. They match
/// `services/api/app/features/registry.py`: a typo here is a flag that is
/// never off. A key the server does not send is treated as on.
abstract final class FeatureKeys {
  static const deepSpa = 'customer.deep_spa';
  static const addons = 'customer.addons';
  static const skipPause = 'customer.skip_pause';
  static const history = 'customer.history';
  static const addVehicle = 'customer.add_vehicle';
  static const subscription = 'customer.subscription';
  static const billingHistory = 'customer.billing_history';
  static const upiPay = 'customer.upi_pay';
  static const help = 'customer.help';
  static const reportIssue = 'customer.report_issue';
  static const complaints = 'customer.complaints';
  static const checkin = 'customer.checkin';
  static const feedback = 'customer.feedback';
  static const managerScreens = 'crew.manager_screens';
  static const crewNotifications = 'crew.notifications';
  static const push = 'common.push';

  /// The flag behind a route, or null when the route is not flagged.
  static String? forPath(String path) {
    if (path == '/customer/deep-spa') return deepSpa;
    if (path == '/customer/history') return history;
    if (path.startsWith('/customer/pay/')) return upiPay;
    if (path.startsWith('/customer/support/faq')) return help;
    if (path.startsWith('/customer/support/report')) return reportIssue;
    if (path.startsWith('/customer/support/complaints')) return complaints;
    if (path.startsWith('/customer/support/checkin')) return checkin;
    final vehicle = RegExp(r'^/customer/vehicles/[^/]+/(\w[\w-]*)$').firstMatch(path);
    return switch (vehicle?.group(1)) {
      'skip-pause' => skipPause,
      'subscription' => subscription,
      'billing' => billingHistory,
      'addons' => addons,
      _ => null,
    };
  }

  /// The flag behind a home-screen quick action, or null.
  static String? forQuickAction(String key) => switch (key) {
        'skip_pause' => skipPause,
        'subscription' => subscription,
        'standalone' => deepSpa,
        'addons' => addons,
        'history' => history,
        'feedback' => feedback,
        _ => null,
      };
}
