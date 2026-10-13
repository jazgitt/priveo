# Test source inventory

Static declaration index; no tests executed. Names may be the first literal segment of a concatenated Dart title. A listed file is not evidence of complete requirement coverage.

| Test declaration | Source |
|---|---|
| test_health_and_config | [services/api/tests/test_api.py:30](../../services/api/tests/test_api.py#L30) |
| test_public_legal_links_and_support_use_configured_values | [services/api/tests/test_api.py:37](../../services/api/tests/test_api.py#L37) |
| test_login_and_home | [services/api/tests/test_api.py:49](../../services/api/tests/test_api.py#L49) |
| test_login_id_decides_the_role | [services/api/tests/test_api.py:58](../../services/api/tests/test_api.py#L58) |
| test_login_id_ignores_case_and_spaces | [services/api/tests/test_api.py:65](../../services/api/tests/test_api.py#L65) |
| test_wrong_password_returns_envelope | [services/api/tests/test_api.py:71](../../services/api/tests/test_api.py#L71) |
| test_unknown_login_looks_like_a_wrong_password | [services/api/tests/test_api.py:79](../../services/api/tests/test_api.py#L79) |
| test_only_the_hash_is_stored | [services/api/tests/test_api.py:84](../../services/api/tests/test_api.py#L84) |
| test_five_wrong_passwords_lock_crew_and_admin | [services/api/tests/test_api.py:91](../../services/api/tests/test_api.py#L91) |
| test_seeding_again_unlocks_the_admin | [services/api/tests/test_api.py:100](../../services/api/tests/test_api.py#L100) |
| test_five_wrong_passwords_block_a_customer_for_15_minutes | [services/api/tests/test_api.py:108](../../services/api/tests/test_api.py#L108) |
| test_a_right_password_clears_the_wrong_count | [services/api/tests/test_api.py:122](../../services/api/tests/test_api.py#L122) |
| test_an_inactive_login_cannot_sign_in | [services/api/tests/test_api.py:130](../../services/api/tests/test_api.py#L130) |
| test_role_is_enforced | [services/api/tests/test_api.py:140](../../services/api/tests/test_api.py#L140) |
| test_refresh_gives_new_tokens_and_the_old_one_stops | [services/api/tests/test_api.py:146](../../services/api/tests/test_api.py#L146) |
| test_logout_ends_the_session_at_once | [services/api/tests/test_api.py:159](../../services/api/tests/test_api.py#L159) |
| test_logout_without_a_token_still_succeeds | [services/api/tests/test_api.py:168](../../services/api/tests/test_api.py#L168) |
| test_admin_signs_out_of_all_devices | [services/api/tests/test_api.py:173](../../services/api/tests/test_api.py#L173) |
| test_only_an_admin_can_sign_out_of_all_devices | [services/api/tests/test_api.py:188](../../services/api/tests/test_api.py#L188) |
| test_admin_phone_signs_out_after_24_idle_hours | [services/api/tests/test_api.py:194](../../services/api/tests/test_api.py#L194) |
| test_demo_logins_are_not_seeded_unless_asked | [services/api/tests/test_api.py:207](../../services/api/tests/test_api.py#L207) |
| test_crew_visits_have_no_customer_details | [services/api/tests/test_api.py:216](../../services/api/tests/test_api.py#L216) |
| test_validation_error_envelope | [services/api/tests/test_api.py:222](../../services/api/tests/test_api.py#L222) |
| test_admin_creates_standalone_customer_without_plan_or_payment | [services/api/tests/test_customer_administration.py:17](../../services/api/tests/test_customer_administration.py#L17) |
| test_onboard_without_import_and_duplicate_email_opens_existing | [services/api/tests/test_customer_administration.py:93](../../services/api/tests/test_customer_administration.py#L93) |
| test_customer_adds_vehicle_in_another_society_and_cannot_confirm_payment | [services/api/tests/test_customer_administration.py:106](../../services/api/tests/test_customer_administration.py#L106) |
| test_customer_cannot_use_an_admins_upload | [services/api/tests/test_customer_administration.py:131](../../services/api/tests/test_customer_administration.py#L131) |
| test_email_correction_invalidates_sessions_and_pending_codes | [services/api/tests/test_customer_administration.py:139](../../services/api/tests/test_customer_administration.py#L139) |
| test_plan_change_waits_for_renewal_and_society_is_immutable | [services/api/tests/test_customer_administration.py:159](../../services/api/tests/test_customer_administration.py#L159) |
| test_activation_anchors_first_payment_and_pending_plan_applies_at_renewal | [services/api/tests/test_customer_administration.py:191](../../services/api/tests/test_customer_administration.py#L191) |
| test_helpers | [services/api/tests/test_customer_home.py:87](../../services/api/tests/test_customer_home.py#L87) |
| test_review_draft_restores_position_and_edits_without_confirmation_or_payment | [services/api/tests/test_customer_home.py:97](../../services/api/tests/test_customer_home.py#L97) |
| test_review_draft_rejects_read_only_foreign_and_invalid_position | [services/api/tests/test_customer_home.py:122](../../services/api/tests/test_customer_home.py#L122) |
| test_home_vehicle_fields_and_rate_action_match_requirements | [services/api/tests/test_customer_home.py:128](../../services/api/tests/test_customer_home.py#L128) |
| test_confirmed_review_cannot_be_changed_by_draft_endpoint | [services/api/tests/test_customer_home.py:140](../../services/api/tests/test_customer_home.py#L140) |
| test_home_shows_the_customers_own_vehicles | [services/api/tests/test_customer_home.py:147](../../services/api/tests/test_customer_home.py#L147) |
| test_a_customer_sees_only_their_own_record | [services/api/tests/test_customer_home.py:167](../../services/api/tests/test_customer_home.py#L167) |
| test_crew_and_admin_cannot_read_customer_screens | [services/api/tests/test_customer_home.py:177](../../services/api/tests/test_customer_home.py#L177) |
| test_a_customer_login_with_no_record_is_told_so | [services/api/tests/test_customer_home.py:185](../../services/api/tests/test_customer_home.py#L185) |
| test_the_review_shows_what_the_admin_entered | [services/api/tests/test_customer_home.py:195](../../services/api/tests/test_customer_home.py#L195) |
| test_confirming_saves_the_changes_and_opens_home | [services/api/tests/test_customer_home.py:210](../../services/api/tests/test_customer_home.py#L210) |
| test_the_gaps_must_be_filled_before_confirming | [services/api/tests/test_customer_home.py:236](../../services/api/tests/test_customer_home.py#L236) |
| test_the_masked_number_on_file_is_accepted_as_it_is | [services/api/tests/test_customer_home.py:254](../../services/api/tests/test_customer_home.py#L254) |
| test_every_vehicle_must_be_reviewed_and_no_other | [services/api/tests/test_customer_home.py:263](../../services/api/tests/test_customer_home.py#L263) |
| test_one_customer_cannot_confirm_with_anothers_vehicle | [services/api/tests/test_customer_home.py:270](../../services/api/tests/test_customer_home.py#L270) |
| test_existing_societies_and_addon_proof_survive_upgrade | [services/api/tests/test_customer_scheduling_upgrade.py:14](../../services/api/tests/test_customer_scheduling_upgrade.py#L14) |
| test_first_sign_in_from_code_to_home | [services/api/tests/test_first_sign_in.py:53](../../services/api/tests/test_first_sign_in.py#L53) |
| test_only_hashes_are_stored | [services/api/tests/test_first_sign_in.py:73](../../services/api/tests/test_first_sign_in.py#L73) |
| test_crew_and_admin_are_asked_for_the_password | [services/api/tests/test_first_sign_in.py:84](../../services/api/tests/test_first_sign_in.py#L84) |
| test_an_email_the_admin_has_not_created_gets_no_code | [services/api/tests/test_first_sign_in.py:89](../../services/api/tests/test_first_sign_in.py#L89) |
| test_an_inactive_customer_gets_no_code | [services/api/tests/test_first_sign_in.py:97](../../services/api/tests/test_first_sign_in.py#L97) |
| test_a_wrong_code_and_then_the_right_one | [services/api/tests/test_first_sign_in.py:103](../../services/api/tests/test_first_sign_in.py#L103) |
| test_five_wrong_codes_cancel_the_code | [services/api/tests/test_first_sign_in.py:110](../../services/api/tests/test_first_sign_in.py#L110) |
| test_a_code_expires_after_10_minutes | [services/api/tests/test_first_sign_in.py:122](../../services/api/tests/test_first_sign_in.py#L122) |
| test_asking_again_within_30_seconds_sends_nothing_new | [services/api/tests/test_first_sign_in.py:132](../../services/api/tests/test_first_sign_in.py#L132) |
| test_at_most_five_codes_in_an_hour | [services/api/tests/test_first_sign_in.py:145](../../services/api/tests/test_first_sign_in.py#L145) |
| test_a_weak_password_is_refused_and_can_be_tried_again | [services/api/tests/test_first_sign_in.py:156](../../services/api/tests/test_first_sign_in.py#L156) |
| test_the_password_token_works_once_and_for_10_minutes | [services/api/tests/test_first_sign_in.py:165](../../services/api/tests/test_first_sign_in.py#L165) |
| test_forgot_password_replaces_the_password_and_signs_out_other_phones | [services/api/tests/test_first_sign_in.py:181](../../services/api/tests/test_first_sign_in.py#L181) |
| test_a_reset_lifts_the_15_minute_block | [services/api/tests/test_first_sign_in.py:198](../../services/api/tests/test_first_sign_in.py#L198) |
| test_crew_cannot_get_a_code | [services/api/tests/test_first_sign_in.py:209](../../services/api/tests/test_first_sign_in.py#L209) |
| test_the_code_is_emailed_and_the_welcome_has_none | [services/api/tests/test_first_sign_in.py:221](../../services/api/tests/test_first_sign_in.py#L221) |
| test_without_a_fixed_code_a_random_one_is_sent | [services/api/tests/test_first_sign_in.py:232](../../services/api/tests/test_first_sign_in.py#L232) |
| test_in_prod_without_resend_no_code_is_made | [services/api/tests/test_first_sign_in.py:243](../../services/api/tests/test_first_sign_in.py#L243) |
| test_a_failed_send_stores_nothing | [services/api/tests/test_first_sign_in.py:251](../../services/api/tests/test_first_sign_in.py#L251) |
| test_the_support_contact_needs_no_sign_in | [services/api/tests/test_first_sign_in.py:263](../../services/api/tests/test_first_sign_in.py#L263) |
| test_the_admin_ends_a_customers_sessions | [services/api/tests/test_first_sign_in.py:268](../../services/api/tests/test_first_sign_in.py#L268) |
| test_customer_paging_reads_past_the_original_limit | [services/api/tests/test_gap_admin_reads.py:11](../../services/api/tests/test_gap_admin_reads.py#L11) |
| test_imported_history_preserves_unknowns_and_is_customer_scoped | [services/api/tests/test_gap_admin_reads.py:30](../../services/api/tests/test_gap_admin_reads.py#L30) |
| test_admin_and_customer_reads_observe_last_committed_profile_edit | [services/api/tests/test_gap_session_audit.py:12](../../services/api/tests/test_gap_session_audit.py#L12) |
| test_customer_logout_all_records_admin_actor_and_reason | [services/api/tests/test_gap_session_audit.py:24](../../services/api/tests/test_gap_session_audit.py#L24) |
| test_admin_logout_all_has_actor_target_count_and_time | [services/api/tests/test_gap_session_audit.py:37](../../services/api/tests/test_gap_session_audit.py#L37) |
| test_failed_audit_insert_rolls_back_session_revocation | [services/api/tests/test_gap_session_audit.py:47](../../services/api/tests/test_gap_session_audit.py#L47) |
| test_helpers | [services/api/tests/test_import.py:73](../../services/api/tests/test_import.py#L73) |
| test_a_trial_run_saves_nothing | [services/api/tests/test_import.py:93](../../services/api/tests/test_import.py#L93) |
| test_the_load | [services/api/tests/test_import.py:99](../../services/api/tests/test_import.py#L99) |
| test_the_report_flags_gaps_without_personal_details | [services/api/tests/test_import.py:151](../../services/api/tests/test_import.py#L151) |
| test_running_it_again_adds_nothing | [services/api/tests/test_import.py:164](../../services/api/tests/test_import.py#L164) |
| test_a_bad_row_is_skipped_and_reported | [services/api/tests/test_import.py:180](../../services/api/tests/test_import.py#L180) |
| test_a_migrated_customer_cannot_sign_in_before_setting_a_password | [services/api/tests/test_import.py:189](../../services/api/tests/test_import.py#L189) |
| test_the_society_column_names_the_society | [services/api/tests/test_import.py:197](../../services/api/tests/test_import.py#L197) |
| test_migrations_build_the_tables_the_models_describe | [services/api/tests/test_migrations.py:13](../../services/api/tests/test_migrations.py#L13) |
| test_the_running_app_knows_every_table | [services/api/tests/test_migrations.py:34](../../services/api/tests/test_migrations.py#L34) |
| test_the_screen_lists_the_offer_and_earlier_requests | [services/api/tests/addons/test_addons.py:17](../../services/api/tests/addons/test_addons.py#L17) |
| test_a_subscriber_requests_deep_spa_and_gets_a_payment | [services/api/tests/addons/test_addons.py:23](../../services/api/tests/addons/test_addons.py#L23) |
| test_the_date_must_be_before_its_9pm_cutoff | [services/api/tests/addons/test_addons.py:40](../../services/api/tests/addons/test_addons.py#L40) |
| test_finish_by_is_in_half_hour_steps_and_the_service_is_offered | [services/api/tests/addons/test_addons.py:49](../../services/api/tests/addons/test_addons.py#L49) |
| test_only_a_vehicle_with_an_active_subscription_can_buy_an_add_on | [services/api/tests/addons/test_addons.py:54](../../services/api/tests/addons/test_addons.py#L54) |
| test_a_retry_with_the_same_key_is_one_request | [services/api/tests/addons/test_addons.py:64](../../services/api/tests/addons/test_addons.py#L64) |
| test_change_and_cancel_follow_the_9pm_rule_and_a_cancelled_add_on_is_not_charged | [services/api/tests/addons/test_addons.py:74](../../services/api/tests/addons/test_addons.py#L74) |
| test_standalone_deep_spa_uses_the_same_spa_payment | [services/api/tests/addons/test_addons.py:95](../../services/api/tests/addons/test_addons.py#L95) |
| test_the_admin_lists_and_updates_requests_without_the_9pm_rule | [services/api/tests/addons/test_addons.py:117](../../services/api/tests/addons/test_addons.py#L117) |
| test_a_changed_add_on_price_is_the_one_offered | [services/api/tests/addons/test_addons.py:133](../../services/api/tests/addons/test_addons.py#L133) |
| test_standalone_retries_create_one_booking_and_one_payment | [services/api/tests/addons/test_standalone_rules.py:12](../../services/api/tests/addons/test_standalone_rules.py#L12) |
| test_standalone_rejects_missing_foreign_subscribed_vehicle_and_late_booking | [services/api/tests/addons/test_standalone_rules.py:22](../../services/api/tests/addons/test_standalone_rules.py#L22) |
| test_standalone_cancel_voids_unpaid_payment_and_respects_cutoff | [services/api/tests/addons/test_standalone_rules.py:32](../../services/api/tests/addons/test_standalone_rules.py#L32) |
| test_my_subscription_shows_the_cycle | [services/api/tests/billing/test_billing.py:25](../../services/api/tests/billing/test_billing.py#L25) |
| test_a_payment_runs_from_due_to_received | [services/api/tests/billing/test_billing.py:36](../../services/api/tests/billing/test_billing.py#L36) |
| test_i_have_paid_twice_is_one_change | [services/api/tests/billing/test_billing.py:65](../../services/api/tests/billing/test_billing.py#L65) |
| test_the_admin_can_reject_and_move_back | [services/api/tests/billing/test_billing.py:74](../../services/api/tests/billing/test_billing.py#L74) |
| test_the_admin_can_record_an_offline_payment | [services/api/tests/billing/test_billing.py:91](../../services/api/tests/billing/test_billing.py#L91) |
| test_over_due_then_inactive_after_seven_days | [services/api/tests/billing/test_billing.py:96](../../services/api/tests/billing/test_billing.py#L96) |
| test_an_over_due_add_on_payment_does_not_make_the_subscription_inactive | [services/api/tests/billing/test_billing.py:127](../../services/api/tests/billing/test_billing.py#L127) |
| test_a_received_payment_is_never_made_over_due | [services/api/tests/billing/test_billing.py:139](../../services/api/tests/billing/test_billing.py#L139) |
| test_an_admin_set_over_due_starts_its_own_seven_days | [services/api/tests/billing/test_billing.py:146](../../services/api/tests/billing/test_billing.py#L146) |
| test_the_next_payment_opens_one_week_before_renewal | [services/api/tests/billing/test_billing.py:157](../../services/api/tests/billing/test_billing.py#L157) |
| test_the_daily_job_creates_the_next_payment_and_follows_a_pause | [services/api/tests/billing/test_billing.py:171](../../services/api/tests/billing/test_billing.py#L171) |
| test_invoice_number_and_the_customers_copy | [services/api/tests/billing/test_billing.py:187](../../services/api/tests/billing/test_billing.py#L187) |
| test_subscription_status_by_the_admin | [services/api/tests/billing/test_billing.py:205](../../services/api/tests/billing/test_billing.py#L205) |
| test_roles_are_enforced_and_unknown_ids_are_not_found | [services/api/tests/billing/test_billing.py:221](../../services/api/tests/billing/test_billing.py#L221) |
| test_a_changed_inactive_after_days_is_the_one_used | [services/api/tests/billing/test_billing.py:232](../../services/api/tests/billing/test_billing.py#L232) |
| test_a_changed_pay_ahead_window_and_upi_id_are_shown | [services/api/tests/billing/test_billing.py:243](../../services/api/tests/billing/test_billing.py#L243) |
| test_reactivation_creates_one_new_due_cycle_and_keeps_old_receipt | [services/api/tests/billing/test_gap_billing.py:25](../../services/api/tests/billing/test_gap_billing.py#L25) |
| test_reactivation_requires_new_date_without_changing_state | [services/api/tests/billing/test_gap_billing.py:46](../../services/api/tests/billing/test_gap_billing.py#L46) |
| test_pause_and_cancel_shift_unpaid_payment_immediately | [services/api/tests/billing/test_gap_billing.py:57](../../services/api/tests/billing/test_gap_billing.py#L57) |
| test_pause_early_end_moves_only_remaining_days | [services/api/tests/billing/test_gap_billing.py:78](../../services/api/tests/billing/test_gap_billing.py#L78) |
| test_previous_activation_pause_and_debt_do_not_inactivate_new_cycle | [services/api/tests/billing/test_gap_billing.py:91](../../services/api/tests/billing/test_gap_billing.py#L91) |
| test_pause_shift_is_idempotent_and_preserves_distinct_future_cycles | [services/api/tests/billing/test_gap_billing.py:108](../../services/api/tests/billing/test_gap_billing.py#L108) |
| test_reactivation_cycle_collision_keeps_old_payment_and_activating_state | [services/api/tests/billing/test_gap_billing.py:122](../../services/api/tests/billing/test_gap_billing.py#L122) |
| test_pause_updates_future_manual_plan_due_date_without_cycle_key | [services/api/tests/billing/test_gap_billing.py:136](../../services/api/tests/billing/test_gap_billing.py#L136) |
| test_payment_submission_has_vehicle_preferences_and_amount_uri | [services/api/tests/billing/test_gap_billing.py:153](../../services/api/tests/billing/test_gap_billing.py#L153) |
| test_payment_paging_does_not_repeat_identical_sort_values | [services/api/tests/billing/test_gap_billing.py:168](../../services/api/tests/billing/test_gap_billing.py#L168) |
| test_inclusive_18_percent_rounds_in_paise_and_balances | [services/api/tests/billing/test_gst_snapshot.py:9](../../services/api/tests/billing/test_gst_snapshot.py#L9) |
| test_issued_tax_remains_immutable_when_configuration_changes | [services/api/tests/billing/test_gst_snapshot.py:18](../../services/api/tests/billing/test_gst_snapshot.py#L18) |
| test_owner_opens_pdf_without_creating_a_second_invoice | [services/api/tests/billing/test_invoice_pdf.py:38](../../services/api/tests/billing/test_invoice_pdf.py#L38) |
| test_pdf_does_not_issue_an_invoice_for_due_or_uninvoiced_received_payment | [services/api/tests/billing/test_invoice_pdf.py:55](../../services/api/tests/billing/test_invoice_pdf.py#L55) |
| test_invoice_pdf_checks_authentication_roles_and_customer_ownership | [services/api/tests/billing/test_invoice_pdf.py:66](../../services/api/tests/billing/test_invoice_pdf.py#L66) |
| test_pdf_preserves_issued_amount_names_and_supplier_details | [services/api/tests/billing/test_invoice_pdf.py:88](../../services/api/tests/billing/test_invoice_pdf.py#L88) |
| test_incomplete_supplier_settings_are_preview_only_and_blocked_outside_dev | [services/api/tests/billing/test_invoice_pdf.py:110](../../services/api/tests/billing/test_invoice_pdf.py#L110) |
| test_legacy_invoice_supplier_details_are_not_silently_backfilled | [services/api/tests/billing/test_invoice_pdf.py:120](../../services/api/tests/billing/test_invoice_pdf.py#L120) |
| test_pdf_escapes_text_and_wraps_long_content | [services/api/tests/billing/test_invoice_pdf.py:133](../../services/api/tests/billing/test_invoice_pdf.py#L133) |
| test_skip_is_accepted_until_9pm_the_evening_before | [services/api/tests/changes/test_changes.py:15](../../services/api/tests/changes/test_changes.py#L15) |
| test_skip_is_refused_from_9pm_the_evening_before | [services/api/tests/changes/test_changes.py:25](../../services/api/tests/changes/test_changes.py#L25) |
| test_the_admin_is_not_bound_by_9pm_but_not_by_the_past | [services/api/tests/changes/test_changes.py:37](../../services/api/tests/changes/test_changes.py#L37) |
| test_skip_twice_or_with_the_same_key_is_one_skip | [services/api/tests/changes/test_changes.py:48](../../services/api/tests/changes/test_changes.py#L48) |
| test_unskip_follows_the_same_cutoff | [services/api/tests/changes/test_changes.py:60](../../services/api/tests/changes/test_changes.py#L60) |
| test_a_date_inside_a_pause_cannot_be_skipped | [services/api/tests/changes/test_changes.py:74](../../services/api/tests/changes/test_changes.py#L74) |
| test_pause_shows_the_visits_and_the_new_renewal_date | [services/api/tests/changes/test_changes.py:84](../../services/api/tests/changes/test_changes.py#L84) |
| test_a_skip_inside_a_pause_is_counted_once | [services/api/tests/changes/test_changes.py:96](../../services/api/tests/changes/test_changes.py#L96) |
| test_pause_validation_and_cutoff | [services/api/tests/changes/test_changes.py:107](../../services/api/tests/changes/test_changes.py#L107) |
| test_ending_a_running_pause_resumes_from_the_next_open_date | [services/api/tests/changes/test_changes.py:127](../../services/api/tests/changes/test_changes.py#L127) |
| test_ending_after_9pm_resumes_a_day_later | [services/api/tests/changes/test_changes.py:142](../../services/api/tests/changes/test_changes.py#L142) |
| test_a_pause_that_has_not_started_is_cancelled | [services/api/tests/changes/test_changes.py:152](../../services/api/tests/changes/test_changes.py#L152) |
| test_cutoff_time_change_is_applied_or_requested_when_frozen | [services/api/tests/changes/test_changes.py:162](../../services/api/tests/changes/test_changes.py#L162) |
| test_upcoming_days_show_skips_pauses_and_what_can_still_change | [services/api/tests/changes/test_changes.py:188](../../services/api/tests/changes/test_changes.py#L188) |
| test_only_active_subscriptions_and_own_vehicles | [services/api/tests/changes/test_changes.py:207](../../services/api/tests/changes/test_changes.py#L207) |
| test_password_format | [services/api/tests/crew/test_crew.py:32](../../services/api/tests/crew/test_crew.py#L32) |
| test_crew_registers_own_session_metadata | [services/api/tests/crew/test_crew.py:37](../../services/api/tests/crew/test_crew.py#L37) |
| test_admin_creates_crew_and_the_password_works_once_shown | [services/api/tests/crew/test_crew.py:52](../../services/api/tests/crew/test_crew.py#L52) |
| test_only_the_admin_manages_crew | [services/api/tests/crew/test_crew.py:69](../../services/api/tests/crew/test_crew.py#L69) |
| test_checks_on_the_new_crew_member | [services/api/tests/crew/test_crew.py:78](../../services/api/tests/crew/test_crew.py#L78) |
| test_a_mobile_number_belongs_to_one_login | [services/api/tests/crew/test_crew.py:90](../../services/api/tests/crew/test_crew.py#L90) |
| test_reset_gives_a_new_password_and_signs_the_phone_out | [services/api/tests/crew/test_crew.py:98](../../services/api/tests/crew/test_crew.py#L98) |
| test_a_locked_login_is_unlocked_by_reset_and_by_unlock | [services/api/tests/crew/test_crew.py:117](../../services/api/tests/crew/test_crew.py#L117) |
| test_unknown_crew_id_is_not_found | [services/api/tests/crew/test_crew.py:141](../../services/api/tests/crew/test_crew.py#L141) |
| test_a_deactivated_crew_member_cannot_sign_in | [services/api/tests/crew/test_crew.py:149](../../services/api/tests/crew/test_crew.py#L149) |
| test_crew_profile_is_the_members_own_and_has_no_customer_data | [services/api/tests/crew/test_crew.py:157](../../services/api/tests/crew/test_crew.py#L157) |
| test_profile_is_for_crew_only_and_needs_a_crew_record | [services/api/tests/crew/test_crew.py:169](../../services/api/tests/crew/test_crew.py#L169) |
| test_fake_sender_logs_the_code_and_keeps_it | [services/api/tests/crew/test_email.py:15](../../services/api/tests/crew/test_email.py#L15) |
| test_fake_sender_welcome_has_no_code | [services/api/tests/crew/test_email.py:23](../../services/api/tests/crew/test_email.py#L23) |
| test_the_mock_code_is_kept_on_dev_and_random_otherwise | [services/api/tests/crew/test_email.py:29](../../services/api/tests/crew/test_email.py#L29) |
| test_a_sender_is_available | [services/api/tests/crew/test_email.py:39](../../services/api/tests/crew/test_email.py#L39) |
| test_templates_and_the_resend_sender | [services/api/tests/crew/test_email.py:43](../../services/api/tests/crew/test_email.py#L43) |
| test_the_prod_fake_never_logs_a_code | [services/api/tests/crew/test_email.py:76](../../services/api/tests/crew/test_email.py#L76) |
| test_send_welcome_for_a_customer | [services/api/tests/crew/test_email.py:83](../../services/api/tests/crew/test_email.py#L83) |
| test_profile_read_and_edit | [services/api/tests/customers_account/test_account.py:36](../../services/api/tests/customers_account/test_account.py#L36) |
| test_failed_email_change_preserves_the_previous_pending_code | [services/api/tests/customers_account/test_account.py:50](../../services/api/tests/customers_account/test_account.py#L50) |
| test_prod_email_change_requires_a_delivery_provider | [services/api/tests/customers_account/test_account.py:70](../../services/api/tests/customers_account/test_account.py#L70) |
| test_email_change_needs_the_code_and_keeps_the_old_email_until_then | [services/api/tests/customers_account/test_account.py:82](../../services/api/tests/customers_account/test_account.py#L82) |
| test_email_change_rejects_a_bad_or_used_email | [services/api/tests/customers_account/test_account.py:104](../../services/api/tests/customers_account/test_account.py#L104) |
| test_change_password | [services/api/tests/customers_account/test_account.py:112](../../services/api/tests/customers_account/test_account.py#L112) |
| test_vehicle_photo_upload_becomes_the_vehicle_photo | [services/api/tests/customers_account/test_account.py:127](../../services/api/tests/customers_account/test_account.py#L127) |
| test_upload_rules | [services/api/tests/customers_account/test_account.py:143](../../services/api/tests/customers_account/test_account.py#L143) |
| test_parking_edit_checks_the_societys_basements | [services/api/tests/customers_account/test_account.py:168](../../services/api/tests/customers_account/test_account.py#L168) |
| test_complaint_photos_and_visit_must_be_the_customers_own | [services/api/tests/customers_account/test_account.py:182](../../services/api/tests/customers_account/test_account.py#L182) |
| test_a_future_month_is_projected_from_the_subscription | [services/api/tests/customer_reads/test_calendar_projection.py:44](../../services/api/tests/customer_reads/test_calendar_projection.py#L44) |
| test_planned_visits_win_over_projected_days | [services/api/tests/customer_reads/test_calendar_projection.py:55](../../services/api/tests/customer_reads/test_calendar_projection.py#L55) |
| test_spa_visit_does_not_replace_the_projected_plan_clean | [services/api/tests/customer_reads/test_calendar_projection.py:65](../../services/api/tests/customer_reads/test_calendar_projection.py#L65) |
| test_no_projection_for_the_past_or_without_an_active_subscription | [services/api/tests/customer_reads/test_calendar_projection.py:76](../../services/api/tests/customer_reads/test_calendar_projection.py#L76) |
| test_skip_pause_and_cutoff_change_on_projected_days | [services/api/tests/customer_reads/test_calendar_projection.py:85](../../services/api/tests/customer_reads/test_calendar_projection.py#L85) |
| test_renewal_dates_move_with_a_pause | [services/api/tests/customer_reads/test_calendar_projection.py:114](../../services/api/tests/customer_reads/test_calendar_projection.py#L114) |
| test_a_requested_cutoff_change_keeps_the_current_value | [services/api/tests/customer_reads/test_calendar_projection.py:127](../../services/api/tests/customer_reads/test_calendar_projection.py#L127) |
| test_missed_visits_show_covered_and_rescheduled_dates | [services/api/tests/customer_reads/test_calendar_projection.py:148](../../services/api/tests/customer_reads/test_calendar_projection.py#L148) |
| test_spa_does_not_cover_a_missed_exterior_job | [services/api/tests/customer_reads/test_calendar_projection.py:174](../../services/api/tests/customer_reads/test_calendar_projection.py#L174) |
| test_assignment_shows_only_for_a_frozen_schedule | [services/api/tests/customer_reads/test_calendar_projection.py:192](../../services/api/tests/customer_reads/test_calendar_projection.py#L192) |
| test_next_service_is_projected_without_a_planned_visit | [services/api/tests/customer_reads/test_calendar_projection.py:230](../../services/api/tests/customer_reads/test_calendar_projection.py#L230) |
| test_preferences_change_the_default_cutoff_and_interior_day | [services/api/tests/customer_reads/test_calendar_projection.py:242](../../services/api/tests/customer_reads/test_calendar_projection.py#L242) |
| test_preferences_after_9pm_apply_from_the_day_after | [services/api/tests/customer_reads/test_calendar_projection.py:272](../../services/api/tests/customer_reads/test_calendar_projection.py#L272) |
| test_calendar_month_lists_visits_with_their_services | [services/api/tests/customer_reads/test_customer_reads.py:10](../../services/api/tests/customer_reads/test_customer_reads.py#L10) |
| test_calendar_can_be_limited_to_one_vehicle | [services/api/tests/customer_reads/test_customer_reads.py:22](../../services/api/tests/customer_reads/test_customer_reads.py#L22) |
| test_calendar_refuses_someone_elses_vehicle_and_a_bad_month | [services/api/tests/customer_reads/test_customer_reads.py:29](../../services/api/tests/customer_reads/test_customer_reads.py#L29) |
| test_visit_detail_carries_the_proof_media | [services/api/tests/customer_reads/test_customer_reads.py:40](../../services/api/tests/customer_reads/test_customer_reads.py#L40) |
| test_visit_of_another_customer_is_not_found | [services/api/tests/customer_reads/test_customer_reads.py:54](../../services/api/tests/customer_reads/test_customer_reads.py#L54) |
| test_history_is_newest_first_and_only_visits_that_are_over | [services/api/tests/customer_reads/test_customer_reads.py:61](../../services/api/tests/customer_reads/test_customer_reads.py#L61) |
| test_next_service_is_the_first_visit_not_over_for_each_vehicle | [services/api/tests/customer_reads/test_customer_reads.py:71](../../services/api/tests/customer_reads/test_customer_reads.py#L71) |
| test_next_service_endpoint | [services/api/tests/customer_reads/test_customer_reads.py:87](../../services/api/tests/customer_reads/test_customer_reads.py#L87) |
| test_vehicles_list_and_detail | [services/api/tests/customer_reads/test_customer_reads.py:91](../../services/api/tests/customer_reads/test_customer_reads.py#L91) |
| test_reads_need_a_customer_sign_in | [services/api/tests/customer_reads/test_customer_reads.py:102](../../services/api/tests/customer_reads/test_customer_reads.py#L102) |
| test_samples_have_five_steps_and_invoice_seller_settings_are_read_only | [services/api/tests/directory/test_directory.py:23](../../services/api/tests/directory/test_directory.py#L23) |
| test_admin_endpoints_need_the_admin_role | [services/api/tests/directory/test_directory.py:50](../../services/api/tests/directory/test_directory.py#L50) |
| test_writes_need_the_admin_role | [services/api/tests/directory/test_directory.py:56](../../services/api/tests/directory/test_directory.py#L56) |
| test_society_create_list_update | [services/api/tests/directory/test_directory.py:65](../../services/api/tests/directory/test_directory.py#L65) |
| test_society_validation | [services/api/tests/directory/test_directory.py:86](../../services/api/tests/directory/test_directory.py#L86) |
| test_society_deactivate_and_no_delete | [services/api/tests/directory/test_directory.py:97](../../services/api/tests/directory/test_directory.py#L97) |
| test_society_with_active_subscriptions_or_crew_cannot_be_deactivated | [services/api/tests/directory/test_directory.py:113](../../services/api/tests/directory/test_directory.py#L113) |
| test_slots_crud_and_rules | [services/api/tests/directory/test_directory.py:143](../../services/api/tests/directory/test_directory.py#L143) |
| test_slots_of_a_society_are_independent | [services/api/tests/directory/test_directory.py:188](../../services/api/tests/directory/test_directory.py#L188) |
| test_plans | [services/api/tests/directory/test_directory.py:199](../../services/api/tests/directory/test_directory.py#L199) |
| test_plan_counts_subscriptions_on_it | [services/api/tests/directory/test_directory.py:235](../../services/api/tests/directory/test_directory.py#L235) |
| test_vehicle_catalogue | [services/api/tests/directory/test_directory.py:250](../../services/api/tests/directory/test_directory.py#L250) |
| test_category_lookup | [services/api/tests/directory/test_directory.py:285](../../services/api/tests/directory/test_directory.py#L285) |
| test_services_defaults_and_update | [services/api/tests/directory/test_directory.py:295](../../services/api/tests/directory/test_directory.py#L295) |
| test_checklist_items | [services/api/tests/directory/test_directory.py:314](../../services/api/tests/directory/test_directory.py#L314) |
| test_the_last_checklist_item_cannot_be_deactivated | [services/api/tests/directory/test_directory.py:353](../../services/api/tests/directory/test_directory.py#L353) |
| test_checklist_lookup_is_active_items_in_order | [services/api/tests/directory/test_directory.py:362](../../services/api/tests/directory/test_directory.py#L362) |
| test_lookups_fall_back_to_the_old_constants_before_the_seed | [services/api/tests/directory/test_directory.py:374](../../services/api/tests/directory/test_directory.py#L374) |
| test_reasons | [services/api/tests/directory/test_directory.py:386](../../services/api/tests/directory/test_directory.py#L386) |
| test_the_last_reason_cannot_be_deactivated | [services/api/tests/directory/test_directory.py:420](../../services/api/tests/directory/test_directory.py#L420) |
| test_settings_list_and_typed_values | [services/api/tests/directory/test_directory.py:431](../../services/api/tests/directory/test_directory.py#L431) |
| test_setting_validation | [services/api/tests/directory/test_directory.py:461](../../services/api/tests/directory/test_directory.py#L461) |
| test_setting_accepts_valid_values | [services/api/tests/directory/test_directory.py:467](../../services/api/tests/directory/test_directory.py#L467) |
| test_unknown_setting | [services/api/tests/directory/test_directory.py:480](../../services/api/tests/directory/test_directory.py#L480) |
| test_patch_settings_is_all_or_nothing | [services/api/tests/directory/test_directory.py:486](../../services/api/tests/directory/test_directory.py#L486) |
| test_settings_cache | [services/api/tests/directory/test_directory.py:498](../../services/api/tests/directory/test_directory.py#L498) |
| test_settings_default_to_the_environment_configuration | [services/api/tests/directory/test_directory.py:524](../../services/api/tests/directory/test_directory.py#L524) |
| test_addon_catalogue | [services/api/tests/directory/test_directory.py:541](../../services/api/tests/directory/test_directory.py#L541) |
| test_customer_reads_need_a_customer | [services/api/tests/directory/test_directory.py:578](../../services/api/tests/directory/test_directory.py#L578) |
| test_changes_are_audited_with_the_admin | [services/api/tests/directory/test_directory.py:588](../../services/api/tests/directory/test_directory.py#L588) |
| test_seed_defaults_inserts_the_stated_defaults | [services/api/tests/directory/test_directory.py:610](../../services/api/tests/directory/test_directory.py#L610) |
| test_seed_defaults_is_idempotent_and_keeps_admin_changes | [services/api/tests/directory/test_directory.py:624](../../services/api/tests/directory/test_directory.py#L624) |
| test_seed_adds_slots_only_to_societies_with_none | [services/api/tests/directory/test_directory.py:650](../../services/api/tests/directory/test_directory.py#L650) |
| test_an_empty_home_is_all_zero | [services/api/tests/home/test_admin_home.py:14](../../services/api/tests/home/test_admin_home.py#L14) |
| test_home_counts_alerts_payments_complaints_and_unscheduled_jobs | [services/api/tests/home/test_admin_home.py:21](../../services/api/tests/home/test_admin_home.py#L21) |
| test_marking_alerts_read_lowers_the_count | [services/api/tests/home/test_admin_home.py:62](../../services/api/tests/home/test_admin_home.py#L62) |
| test_day_schedule_groups_jobs_by_crew_and_hides_the_customer | [services/api/tests/home/test_admin_home.py:70](../../services/api/tests/home/test_admin_home.py#L70) |
| test_day_schedule_without_a_society_and_with_an_empty_day | [services/api/tests/home/test_admin_home.py:91](../../services/api/tests/home/test_admin_home.py#L91) |
| test_day_schedule_is_for_admins_only | [services/api/tests/home/test_admin_home.py:104](../../services/api/tests/home/test_admin_home.py#L104) |
| test_the_flow_returns_a_signed_url_and_confirms_the_file | [services/api/tests/media/test_uploads.py:16](../../services/api/tests/media/test_uploads.py#L16) |
| test_formats_and_sizes_follow_rule_17 | [services/api/tests/media/test_uploads.py:42](../../services/api/tests/media/test_uploads.py#L42) |
| test_a_crew_member_cannot_upload_to_a_job_that_is_not_theirs | [services/api/tests/media/test_uploads.py:62](../../services/api/tests/media/test_uploads.py#L62) |
| test_the_signed_url_cannot_be_forged_or_replayed | [services/api/tests/media/test_uploads.py:70](../../services/api/tests/media/test_uploads.py#L70) |
| test_an_oversized_body_is_refused | [services/api/tests/media/test_uploads.py:89](../../services/api/tests/media/test_uploads.py#L89) |
| test_another_crew_member_cannot_confirm_my_upload | [services/api/tests/media/test_uploads.py:97](../../services/api/tests/media/test_uploads.py#L97) |
| test_exact_media_limits_on_upload_request | [services/api/tests/media/test_uploads.py:110](../../services/api/tests/media/test_uploads.py#L110) |
| test_exact_media_limit_refused_at_signed_put_and_confirmation | [services/api/tests/media/test_uploads.py:121](../../services/api/tests/media/test_uploads.py#L121) |
| test_rc_document_keeps_its_inclusive_five_mb_limit | [services/api/tests/media/test_uploads.py:140](../../services/api/tests/media/test_uploads.py#L140) |
| test_a_visit_completed_tells_the_customer_once | [services/api/tests/notifications/test_events.py:72](../../services/api/tests/notifications/test_events.py#L72) |
| test_a_switched_off_event_is_not_sent | [services/api/tests/notifications/test_events.py:86](../../services/api/tests/notifications/test_events.py#L86) |
| test_skipped_by_operations_tells_the_customer_and_the_crew | [services/api/tests/notifications/test_events.py:96](../../services/api/tests/notifications/test_events.py#L96) |
| test_could_not_complete_alerts_the_admin_only | [services/api/tests/notifications/test_events.py:107](../../services/api/tests/notifications/test_events.py#L107) |
| test_freeze_tells_each_crew_member_and_their_trainee_once | [services/api/tests/notifications/test_events.py:120](../../services/api/tests/notifications/test_events.py#L120) |
| test_freeze_due_tells_the_crew | [services/api/tests/notifications/test_events.py:137](../../services/api/tests/notifications/test_events.py#L137) |
| test_a_late_assignment_tells_the_new_crew_member_and_alerts_the_admin | [services/api/tests/notifications/test_events.py:145](../../services/api/tests/notifications/test_events.py#L145) |
| test_a_visit_nobody_can_take_goes_to_needs_scheduling_alert | [services/api/tests/notifications/test_events.py:166](../../services/api/tests/notifications/test_events.py#L166) |
| test_a_skip_after_the_freeze_removes_the_job_and_alerts_the_admin | [services/api/tests/notifications/test_events.py:176](../../services/api/tests/notifications/test_events.py#L176) |
| test_a_paused_job_removes_it_from_the_crew | [services/api/tests/notifications/test_events.py:187](../../services/api/tests/notifications/test_events.py#L187) |
| test_a_customer_skip_tells_the_customer | [services/api/tests/notifications/test_events.py:196](../../services/api/tests/notifications/test_events.py#L196) |
| test_admin_skip_keeps_the_explicit_skip_notification | [services/api/tests/notifications/test_events.py:201](../../services/api/tests/notifications/test_events.py#L201) |
| test_a_manager_reassign_tells_both_and_the_trainee | [services/api/tests/notifications/test_events.py:208](../../services/api/tests/notifications/test_events.py#L208) |
| test_a_skipped_job_leaves_the_crew_cards | [services/api/tests/notifications/test_events.py:225](../../services/api/tests/notifications/test_events.py#L225) |
| test_the_crew_inbox_devices_and_read | [services/api/tests/notifications/test_events.py:237](../../services/api/tests/notifications/test_events.py#L237) |
| test_a_customer_cannot_open_the_crew_inbox | [services/api/tests/notifications/test_events.py:258](../../services/api/tests/notifications/test_events.py#L258) |
| test_a_crew_member_has_no_switches | [services/api/tests/notifications/test_events.py:265](../../services/api/tests/notifications/test_events.py#L265) |
| test_preferences_default_on_and_change_one_at_a_time | [services/api/tests/notifications/test_events.py:273](../../services/api/tests/notifications/test_events.py#L273) |
| test_the_support_bridge_writes_the_inbox_and_follows_the_switch | [services/api/tests/notifications/test_events.py:292](../../services/api/tests/notifications/test_events.py#L292) |
| test_admin_push_goes_to_admin_phones | [services/api/tests/notifications/test_events.py:304](../../services/api/tests/notifications/test_events.py#L304) |
| test_reminder_days | [services/api/tests/notifications/test_events.py:314](../../services/api/tests/notifications/test_events.py#L314) |
| test_renewal_reminders_follow_the_schedule_and_stop | [services/api/tests/notifications/test_events.py:330](../../services/api/tests/notifications/test_events.py#L330) |
| test_cron_needs_the_secret | [services/api/tests/notifications/test_events.py:366](../../services/api/tests/notifications/test_events.py#L366) |
| test_every_cron_job_runs_and_can_run_again | [services/api/tests/notifications/test_events.py:375](../../services/api/tests/notifications/test_events.py#L375) |
| test_the_cron_jobs_do_their_work | [services/api/tests/notifications/test_events.py:386](../../services/api/tests/notifications/test_events.py#L386) |
| test_inbox_lists_newest_first_with_unread_count | [services/api/tests/notifications/test_notifications.py:37](../../services/api/tests/notifications/test_notifications.py#L37) |
| test_mark_one_and_mark_all_read | [services/api/tests/notifications/test_notifications.py:49](../../services/api/tests/notifications/test_notifications.py#L49) |
| test_a_message_of_someone_else_cannot_be_marked | [services/api/tests/notifications/test_notifications.py:61](../../services/api/tests/notifications/test_notifications.py#L61) |
| test_device_tokens_register_move_and_remove | [services/api/tests/notifications/test_notifications.py:69](../../services/api/tests/notifications/test_notifications.py#L69) |
| test_bad_device_body_and_unknown_event | [services/api/tests/notifications/test_notifications.py:85](../../services/api/tests/notifications/test_notifications.py#L85) |
| test_inbox_needs_a_customer_sign_in | [services/api/tests/notifications/test_notifications.py:93](../../services/api/tests/notifications/test_notifications.py#L93) |
| test_standalone_without_subscription_is_scheduled_unpaid_and_tracks_completion | [services/api/tests/scheduling/test_addon_lifecycle.py:14](../../services/api/tests/scheduling/test_addon_lifecycle.py#L14) |
| test_booking_reaches_scheduler_without_payment_and_has_its_own_visit | [services/api/tests/scheduling/test_addon_lifecycle.py:65](../../services/api/tests/scheduling/test_addon_lifecycle.py#L65) |
| test_frozen_change_is_a_request_and_cancel_removes_spa_only | [services/api/tests/scheduling/test_addon_lifecycle.py:93](../../services/api/tests/scheduling/test_addon_lifecycle.py#L93) |
| test_unfit_booking_stays_requested_and_late_additions_do_not_move_frozen_jobs | [services/api/tests/scheduling/test_addon_lifecycle.py:129](../../services/api/tests/scheduling/test_addon_lifecycle.py#L129) |
| test_swap_failure_is_atomic_and_suggestions_do_not_write | [services/api/tests/scheduling/test_addon_lifecycle.py:147](../../services/api/tests/scheduling/test_addon_lifecycle.py#L147) |
| test_only_admin_can_enable_planning_with_a_time | [services/api/tests/scheduling/test_automatic_planning.py:23](../../services/api/tests/scheduling/test_automatic_planning.py#L23) |
| test_planning_is_disabled_and_enabling_requires_time | [services/api/tests/scheduling/test_automatic_planning.py:34](../../services/api/tests/scheduling/test_automatic_planning.py#L34) |
| test_draft_is_created_after_ist_time_once_and_never_frozen | [services/api/tests/scheduling/test_automatic_planning.py:41](../../services/api/tests/scheduling/test_automatic_planning.py#L41) |
| test_existing_manual_schedule_is_preserved | [services/api/tests/scheduling/test_automatic_planning.py:52](../../services/api/tests/scheduling/test_automatic_planning.py#L52) |
| test_failure_alerts_and_retries_same_draft | [services/api/tests/scheduling/test_automatic_planning.py:63](../../services/api/tests/scheduling/test_automatic_planning.py#L63) |
| test_next_period_handles_week_and_year_and_leap_month | [services/api/tests/scheduling/test_automatic_planning.py:80](../../services/api/tests/scheduling/test_automatic_planning.py#L80) |
| test_an_onboarded_crew_member_gets_jobs | [services/api/tests/scheduling/test_crew_directory.py:74](../../services/api/tests/scheduling/test_crew_directory.py#L74) |
| test_weekday_hours_and_exceptions_shape_the_window | [services/api/tests/scheduling/test_crew_directory.py:93](../../services/api/tests/scheduling/test_crew_directory.py#L93) |
| test_the_single_window_still_applies_without_weekday_hours | [services/api/tests/scheduling/test_crew_directory.py:115](../../services/api/tests/scheduling/test_crew_directory.py#L115) |
| test_a_day_off_in_new_hours_sends_open_jobs_to_needs_scheduling | [services/api/tests/scheduling/test_crew_directory.py:121](../../services/api/tests/scheduling/test_crew_directory.py#L121) |
| test_an_exception_releases_jobs_and_can_be_edited_and_removed | [services/api/tests/scheduling/test_crew_directory.py:137](../../services/api/tests/scheduling/test_crew_directory.py#L137) |
| test_a_range_of_exceptions_and_past_dates | [services/api/tests/scheduling/test_crew_directory.py:172](../../services/api/tests/scheduling/test_crew_directory.py#L172) |
| test_a_deactivated_crew_member_is_not_scheduled_and_cannot_sign_in | [services/api/tests/scheduling/test_crew_directory.py:186](../../services/api/tests/scheduling/test_crew_directory.py#L186) |
| test_a_job_in_progress_stops_deactivation | [services/api/tests/scheduling/test_crew_directory.py:220](../../services/api/tests/scheduling/test_crew_directory.py#L220) |
| test_a_trainee_is_paired_with_a_member_and_gets_their_jobs | [services/api/tests/scheduling/test_crew_directory.py:234](../../services/api/tests/scheduling/test_crew_directory.py#L234) |
| test_pairing_rules | [services/api/tests/scheduling/test_crew_directory.py:274](../../services/api/tests/scheduling/test_crew_directory.py#L274) |
| test_a_member_made_trainee_loses_open_jobs | [services/api/tests/scheduling/test_crew_directory.py:297](../../services/api/tests/scheduling/test_crew_directory.py#L297) |
| test_edit_details_and_login_id | [services/api/tests/scheduling/test_crew_directory.py:313](../../services/api/tests/scheduling/test_crew_directory.py#L313) |
| test_admin_lists_and_ends_a_crew_members_sessions | [services/api/tests/scheduling/test_crew_directory.py:330](../../services/api/tests/scheduling/test_crew_directory.py#L330) |
| test_only_the_admin_changes_crew | [services/api/tests/scheduling/test_crew_directory.py:350](../../services/api/tests/scheduling/test_crew_directory.py#L350) |
| test_changes_made_before_planning_are_kept | [services/api/tests/scheduling/test_customer_changes_planned.py:13](../../services/api/tests/scheduling/test_customer_changes_planned.py#L13) |
| test_skip_extends_once_moves_unreceived_payment_and_preserves_failure | [services/api/tests/scheduling/test_operations.py:62](../../services/api/tests/scheduling/test_operations.py#L62) |
| test_next_day_internal_retry_preserves_frozen_work_and_calendar_link | [services/api/tests/scheduling/test_operations.py:102](../../services/api/tests/scheduling/test_operations.py#L102) |
| test_spa_retry_has_one_job_and_booking_completes_from_retry | [services/api/tests/scheduling/test_operations.py:142](../../services/api/tests/scheduling/test_operations.py#L142) |
| test_completed_and_external_jobs_cannot_be_repeated_and_roles_are_enforced | [services/api/tests/scheduling/test_operations.py:167](../../services/api/tests/scheduling/test_operations.py#L167) |
| test_unplaced_retry_survives_rerun_and_stays_on_needs_scheduling | [services/api/tests/scheduling/test_operations.py:196](../../services/api/tests/scheduling/test_operations.py#L196) |
| test_past_retry_rolls_back_and_audit_filters_find_the_actual_actor | [services/api/tests/scheduling/test_operations.py:216](../../services/api/tests/scheduling/test_operations.py#L216) |
| test_freeze_cutoff_is_8_pm_the_day_before_the_first_day | [services/api/tests/scheduling/test_rules.py:7](../../services/api/tests/scheduling/test_rules.py#L7) |
| test_customers_change_until_9_pm_the_day_before | [services/api/tests/scheduling/test_rules.py:12](../../services/api/tests/scheduling/test_rules.py#L12) |
| test_a_visit_is_completed_only_when_all_jobs_are_done_or_skipped | [services/api/tests/scheduling/test_rules.py:18](../../services/api/tests/scheduling/test_rules.py#L18) |
| test_trainees_and_absent_crew_add_no_capacity | [services/api/tests/scheduling/test_rules.py:27](../../services/api/tests/scheduling/test_rules.py#L27) |
| test_a_run_makes_a_draft_and_respects_capacity | [services/api/tests/scheduling/test_scheduling_api.py:27](../../services/api/tests/scheduling/test_scheduling_api.py#L27) |
| test_a_manual_change_survives_a_rerun | [services/api/tests/scheduling/test_scheduling_api.py:55](../../services/api/tests/scheduling/test_scheduling_api.py#L55) |
| test_taking_a_job_off_is_kept_on_a_rerun | [services/api/tests/scheduling/test_scheduling_api.py:78](../../services/api/tests/scheduling/test_scheduling_api.py#L78) |
| test_a_move_that_overlaps_or_leaves_the_hours_is_refused | [services/api/tests/scheduling/test_scheduling_api.py:91](../../services/api/tests/scheduling/test_scheduling_api.py#L91) |
| test_interior_day_and_deep_spa_are_jobs_of_their_own | [services/api/tests/scheduling/test_scheduling_api.py:107](../../services/api/tests/scheduling/test_scheduling_api.py#L107) |
| test_inactive_and_trainee_do_not_count | [services/api/tests/scheduling/test_scheduling_api.py:125](../../services/api/tests/scheduling/test_scheduling_api.py#L125) |
| test_a_crew_exception_removes_that_days_capacity | [services/api/tests/scheduling/test_scheduling_api.py:137](../../services/api/tests/scheduling/test_scheduling_api.py#L137) |
| test_freeze_and_unfreeze_with_the_code | [services/api/tests/scheduling/test_scheduling_api.py:146](../../services/api/tests/scheduling/test_scheduling_api.py#L146) |
| test_removing_from_a_frozen_schedule_needs_no_code | [services/api/tests/scheduling/test_scheduling_api.py:175](../../services/api/tests/scheduling/test_scheduling_api.py#L175) |
| test_a_late_visit_is_placed_on_a_frozen_schedule_without_moving_others | [services/api/tests/scheduling/test_scheduling_api.py:189](../../services/api/tests/scheduling/test_scheduling_api.py#L189) |
| test_the_freeze_cutoff_time_freezes_drafts | [services/api/tests/scheduling/test_scheduling_api.py:209](../../services/api/tests/scheduling/test_scheduling_api.py#L209) |
| test_the_crew_day_shows_only_frozen_work_and_no_customer_details | [services/api/tests/scheduling/test_scheduling_api.py:222](../../services/api/tests/scheduling/test_scheduling_api.py#L222) |
| test_a_trainee_sees_the_paired_members_jobs | [services/api/tests/scheduling/test_scheduling_api.py:246](../../services/api/tests/scheduling/test_scheduling_api.py#L246) |
| test_next_service_for_the_customer | [services/api/tests/scheduling/test_scheduling_api.py:259](../../services/api/tests/scheduling/test_scheduling_api.py#L259) |
| test_a_visit_completes_only_when_all_its_jobs_are_done | [services/api/tests/scheduling/test_scheduling_api.py:284](../../services/api/tests/scheduling/test_scheduling_api.py#L284) |
| test_scheduling_endpoints_are_for_their_role | [services/api/tests/scheduling/test_scheduling_api.py:299](../../services/api/tests/scheduling/test_scheduling_api.py#L299) |
| test_a_changed_unfreeze_code_is_the_one_that_works | [services/api/tests/scheduling/test_scheduling_api.py:313](../../services/api/tests/scheduling/test_scheduling_api.py#L313) |
| test_a_changed_freeze_hour_moves_the_cutoff | [services/api/tests/scheduling/test_scheduling_api.py:327](../../services/api/tests/scheduling/test_scheduling_api.py#L327) |
| test_a_changed_service_duration_is_used_for_new_jobs | [services/api/tests/scheduling/test_scheduling_api.py:338](../../services/api/tests/scheduling/test_scheduling_api.py#L338) |
| test_capacity_is_respected | [services/api/tests/scheduling/test_solver.py:22](../../services/api/tests/scheduling/test_solver.py#L22) |
| test_a_hand_made_placement_is_kept_and_blocks_its_time | [services/api/tests/scheduling/test_solver.py:33](../../services/api/tests/scheduling/test_solver.py#L33) |
| test_a_deep_spa_does_not_fit_a_short_window | [services/api/tests/scheduling/test_solver.py:43](../../services/api/tests/scheduling/test_solver.py#L43) |
| test_a_job_that_misses_its_cutoff_is_placed_and_flagged_late | [services/api/tests/scheduling/test_solver.py:49](../../services/api/tests/scheduling/test_solver.py#L49) |
| test_jobs_that_can_meet_the_cutoff_do | [services/api/tests/scheduling/test_solver.py:55](../../services/api/tests/scheduling/test_solver.py#L55) |
| test_one_vehicle_is_not_worked_on_twice_at_once | [services/api/tests/scheduling/test_solver.py:62](../../services/api/tests/scheduling/test_solver.py#L62) |
| test_no_crew_leaves_everything_unplaced | [services/api/tests/scheduling/test_solver.py:70](../../services/api/tests/scheduling/test_solver.py#L70) |
| test_service_cannot_cross_a_gap_between_working_slots | [services/api/tests/scheduling/test_solver.py:75](../../services/api/tests/scheduling/test_solver.py#L75) |
| test_the_same_input_gives_the_same_plan | [services/api/tests/scheduling/test_solver.py:85](../../services/api/tests/scheduling/test_solver.py#L85) |
| test_preference_is_own_admin_only_and_persists | [services/api/tests/support/test_alert_email_delivery.py:33](../../services/api/tests/support/test_alert_email_delivery.py#L33) |
| test_disabled_email_preserves_inbox_and_push | [services/api/tests/support/test_alert_email_delivery.py:41](../../services/api/tests/support/test_alert_email_delivery.py#L41) |
| test_delivery_retries_once_due_with_same_key_and_no_duplicate_success | [services/api/tests/support/test_alert_email_delivery.py:48](../../services/api/tests/support/test_alert_email_delivery.py#L48) |
| test_turning_off_email_stops_pending_delivery | [services/api/tests/support/test_alert_email_delivery.py:65](../../services/api/tests/support/test_alert_email_delivery.py#L65) |
| test_retry_exhaustion_is_bounded_and_does_not_lose_inbox | [services/api/tests/support/test_alert_email_delivery.py:74](../../services/api/tests/support/test_alert_email_delivery.py#L74) |
| test_four_hour_boundary_alerts_once | [services/api/tests/support/test_alert_email_delivery.py:85](../../services/api/tests/support/test_alert_email_delivery.py#L85) |
| test_address_change_does_not_redirect_an_old_pending_email | [services/api/tests/support/test_alert_email_delivery.py:99](../../services/api/tests/support/test_alert_email_delivery.py#L99) |
| test_push_failure_does_not_suppress_email_or_inbox | [services/api/tests/support/test_alert_email_delivery.py:109](../../services/api/tests/support/test_alert_email_delivery.py#L109) |
| test_resend_alert_escapes_html_and_sends_stable_provider_key | [services/api/tests/support/test_alert_email_delivery.py:117](../../services/api/tests/support/test_alert_email_delivery.py#L117) |
| test_escalation_failure_rolls_back_marker_and_alert | [services/api/tests/support/test_alert_email_delivery.py:135](../../services/api/tests/support/test_alert_email_delivery.py#L135) |
| test_rating_unknown_visit_has_no_side_effects | [services/api/tests/support/test_rating_authorization.py:13](../../services/api/tests/support/test_rating_authorization.py#L13) |
| test_rating_requires_completed_visit | [services/api/tests/support/test_rating_authorization.py:21](../../services/api/tests/support/test_rating_authorization.py#L21) |
| test_rating_foreign_completed_visit_is_rejected | [services/api/tests/support/test_rating_authorization.py:30](../../services/api/tests/support/test_rating_authorization.py#L30) |
| test_rating_canonical_id_updates_one_record | [services/api/tests/support/test_rating_authorization.py:50](../../services/api/tests/support/test_rating_authorization.py#L50) |
| test_other_roles_cannot_rate | [services/api/tests/support/test_rating_authorization.py:60](../../services/api/tests/support/test_rating_authorization.py#L60) |
| test_complaint_goes_from_customer_to_admin_and_back | [services/api/tests/support/test_support.py:28](../../services/api/tests/support/test_support.py#L28) |
| test_complaint_validation | [services/api/tests/support/test_support.py:86](../../services/api/tests/support/test_support.py#L86) |
| test_numbers_count_up_and_newest_is_first | [services/api/tests/support/test_support.py:94](../../services/api/tests/support/test_support.py#L94) |
| test_a_customer_sees_only_their_own_complaints | [services/api/tests/support/test_support.py:101](../../services/api/tests/support/test_support.py#L101) |
| test_roles_are_enforced | [services/api/tests/support/test_support.py:113](../../services/api/tests/support/test_support.py#L113) |
| test_overdue_complaint_is_highlighted_and_alerted_once | [services/api/tests/support/test_support.py:121](../../services/api/tests/support/test_support.py#L121) |
| test_admin_filters_complaints | [services/api/tests/support/test_support.py:135](../../services/api/tests/support/test_support.py#L135) |
| test_a_status_change_without_a_change_sends_nothing | [services/api/tests/support/test_support.py:149](../../services/api/tests/support/test_support.py#L149) |
| test_contact_comes_from_settings | [services/api/tests/support/test_support.py:158](../../services/api/tests/support/test_support.py#L158) |
| test_a_saved_helpline_and_checkin_window_win_over_the_environment | [services/api/tests/support/test_support.py:172](../../services/api/tests/support/test_support.py#L172) |
| test_options_start_with_the_owner_lists_and_admin_edits_them | [services/api/tests/support/test_support.py:181](../../services/api/tests/support/test_support.py#L181) |
| test_renaming_an_option_keeps_earlier_feedback_under_its_original_name | [services/api/tests/support/test_support.py:207](../../services/api/tests/support/test_support.py#L207) |
| test_feedback_needs_a_rating_or_a_comment | [services/api/tests/support/test_support.py:218](../../services/api/tests/support/test_support.py#L218) |
| test_visit_rating_tags_follow_the_stars | [services/api/tests/support/test_support.py:238](../../services/api/tests/support/test_support.py#L238) |
| test_admin_complaint_lists_vehicle_and_opens_owned_linked_visit | [services/api/tests/support/test_support.py:262](../../services/api/tests/support/test_support.py#L262) |
| test_cycle_for | [services/api/tests/support/test_support.py:284](../../services/api/tests/support/test_support.py#L284) |
| test_checkin_is_due_in_the_last_four_days_and_saved_once | [services/api/tests/support/test_support.py:291](../../services/api/tests/support/test_support.py#L291) |
| test_a_changed_checkin_window_is_the_one_used | [services/api/tests/support/test_support.py:314](../../services/api/tests/support/test_support.py#L314) |
| test_checkin_rules | [services/api/tests/support/test_support.py:322](../../services/api/tests/support/test_support.py#L322) |
| test_checkin_push_goes_out_four_days_before_renewal | [services/api/tests/support/test_support.py:336](../../services/api/tests/support/test_support.py#L336) |
| test_alert_list_and_read_state | [services/api/tests/support/test_support.py:346](../../services/api/tests/support/test_support.py#L346) |
| test_a_failing_notifier_does_not_lose_the_alert | [services/api/tests/support/test_support.py:364](../../services/api/tests/support/test_support.py#L364) |
| test_display_id | [services/api/tests/support/test_support.py:373](../../services/api/tests/support/test_support.py#L373) |
| test_migration_builds_the_support_tables | [services/api/tests/support/test_support.py:379](../../services/api/tests/support/test_support.py#L379) |
| test_rating_bounds | [services/api/tests/support/test_support.py:402](../../services/api/tests/support/test_support.py#L402) |
| test_faq_is_an_ordered_list_for_customers_only | [services/api/tests/support/test_wp8.py:18](../../services/api/tests/support/test_wp8.py#L18) |
| test_checkin_categories_are_the_six_owner_categories | [services/api/tests/support/test_wp8.py:30](../../services/api/tests/support/test_wp8.py#L30) |
| test_migration_tops_up_an_existing_checkin_list | [services/api/tests/support/test_wp8.py:36](../../services/api/tests/support/test_wp8.py#L36) |
| test_issued_checklist_keeps_labels_order_and_required_items | [services/api/tests/visits/test_checklist_snapshots.py:13](../../services/api/tests/visits/test_checklist_snapshots.py#L13) |
| test_customer_completed_history_uses_snapshot_and_original_tick_times | [services/api/tests/visits/test_checklist_snapshots.py:40](../../services/api/tests/visits/test_checklist_snapshots.py#L40) |
| test_legacy_backfill_marks_unknown_labels_and_excludes_new_items_from_completed_work | [services/api/tests/visits/test_checklist_snapshots.py:64](../../services/api/tests/visits/test_checklist_snapshots.py#L64) |
| test_completed_calendar_has_finish_and_check_summary | [services/api/tests/visits/test_checklist_snapshots.py:95](../../services/api/tests/visits/test_checklist_snapshots.py#L95) |
| test_cards_for_a_day_show_the_vehicle_and_never_the_customer | [services/api/tests/visits/test_crew_jobs.py:20](../../services/api/tests/visits/test_crew_jobs.py#L20) |
| test_a_member_sees_only_their_own_jobs | [services/api/tests/visits/test_crew_jobs.py:48](../../services/api/tests/visits/test_crew_jobs.py#L48) |
| test_a_trainee_sees_and_does_the_paired_members_jobs | [services/api/tests/visits/test_crew_jobs.py:59](../../services/api/tests/visits/test_crew_jobs.py#L59) |
| test_start_moves_a_job_to_in_progress | [services/api/tests/visits/test_crew_jobs.py:77](../../services/api/tests/visits/test_crew_jobs.py#L77) |
| test_a_job_cannot_complete_until_checklist_and_proof_are_done | [services/api/tests/visits/test_crew_jobs.py:90](../../services/api/tests/visits/test_crew_jobs.py#L90) |
| test_an_unconfirmed_upload_blocks_completion | [services/api/tests/visits/test_crew_jobs.py:119](../../services/api/tests/visits/test_crew_jobs.py#L119) |
| test_a_completed_job_cannot_be_changed | [services/api/tests/visits/test_crew_jobs.py:144](../../services/api/tests/visits/test_crew_jobs.py#L144) |
| test_a_visit_is_completed_only_when_all_its_jobs_are_done | [services/api/tests/visits/test_crew_jobs.py:163](../../services/api/tests/visits/test_crew_jobs.py#L163) |
| test_could_not_complete_needs_a_listed_reason | [services/api/tests/visits/test_crew_jobs.py:183](../../services/api/tests/visits/test_crew_jobs.py#L183) |
| test_could_not_complete_can_carry_a_confirmed_photo | [services/api/tests/visits/test_crew_jobs.py:196](../../services/api/tests/visits/test_crew_jobs.py#L196) |
| test_a_draft_schedule_is_not_shown_to_the_crew | [services/api/tests/visits/test_crew_jobs.py:212](../../services/api/tests/visits/test_crew_jobs.py#L212) |
| test_profile_photo_needs_a_confirmed_upload | [services/api/tests/visits/test_crew_jobs.py:222](../../services/api/tests/visits/test_crew_jobs.py#L222) |
| test_only_crew_can_use_the_crew_routes | [services/api/tests/visits/test_crew_jobs.py:242](../../services/api/tests/visits/test_crew_jobs.py#L242) |
| test_a_switched_off_checklist_item_and_reason_follow_the_admin | [services/api/tests/visits/test_crew_jobs.py:248](../../services/api/tests/visits/test_crew_jobs.py#L248) |
| test_a_changed_proof_minimum_is_the_one_required | [services/api/tests/visits/test_crew_jobs.py:278](../../services/api/tests/visits/test_crew_jobs.py#L278) |
| test_a_member_cannot_use_manager_routes | [services/api/tests/visits/test_manager.py:6](../../services/api/tests/visits/test_manager.py#L6) |
| test_schedule_groups_the_societys_jobs_by_crew_member | [services/api/tests/visits/test_manager.py:15](../../services/api/tests/visits/test_manager.py#L15) |
| test_a_manager_marks_another_crews_job_could_not_complete | [services/api/tests/visits/test_manager.py:35](../../services/api/tests/visits/test_manager.py#L35) |
| test_a_manager_can_skip_a_job_and_the_visit_completes | [services/api/tests/visits/test_manager.py:49](../../services/api/tests/visits/test_manager.py#L49) |
| test_reassign_moves_the_job_and_follows_the_trainee | [services/api/tests/visits/test_manager.py:62](../../services/api/tests/visits/test_manager.py#L62) |
| test_a_manager_cannot_reach_another_societys_job | [services/api/tests/visits/test_manager.py:87](../../services/api/tests/visits/test_manager.py#L87) |
| test_a_member_cannot_use_attendance_or_hours | [services/api/tests/visits/test_manager_ops.py:33](../../services/api/tests/visits/test_manager_ops.py#L33) |
| test_marking_absent_changes_the_list_and_releases_open_jobs | [services/api/tests/visits/test_manager_ops.py:40](../../services/api/tests/visits/test_manager_ops.py#L40) |
| test_a_frozen_job_goes_to_someone_who_fits | [services/api/tests/visits/test_manager_ops.py:66](../../services/api/tests/visits/test_manager_ops.py#L66) |
| test_late_start_needs_a_time_and_dates_in_the_past_are_refused | [services/api/tests/visits/test_manager_ops.py:87](../../services/api/tests/visits/test_manager_ops.py#L87) |
| test_another_society_is_not_found | [services/api/tests/visits/test_manager_ops.py:102](../../services/api/tests/visits/test_manager_ops.py#L102) |
| test_hours_are_listed_and_changed_and_capacity_follows | [services/api/tests/visits/test_manager_ops.py:120](../../services/api/tests/visits/test_manager_ops.py#L120) |
| test_bad_hours_are_refused | [services/api/tests/visits/test_manager_ops.py:142](../../services/api/tests/visits/test_manager_ops.py#L142) |
| test_reassign_to_someone_on_leave_is_refused | [services/api/tests/visits/test_manager_ops.py:156](../../services/api/tests/visits/test_manager_ops.py#L156) |
| test_reassign_outside_hours_and_overlap_are_refused | [services/api/tests/visits/test_manager_ops.py:176](../../services/api/tests/visits/test_manager_ops.py#L176) |
| test_reassign_to_the_same_person_and_a_started_job_are_refused | [services/api/tests/visits/test_manager_ops.py:198](../../services/api/tests/visits/test_manager_ops.py#L198) |
| test_an_unplaced_job_gets_the_first_free_time | [services/api/tests/visits/test_manager_ops.py:217](../../services/api/tests/visits/test_manager_ops.py#L217) |
| test_skipping_external_extends_the_plan_by_one_day_once | [services/api/tests/visits/test_manager_ops.py:233](../../services/api/tests/visits/test_manager_ops.py#L233) |
| test_skipping_internal_does_not_extend_the_plan | [services/api/tests/visits/test_manager_ops.py:249](../../services/api/tests/visits/test_manager_ops.py#L249) |
| test_customer_sees_proof_checklist_crew_and_finish_time | [services/api/tests/visits/test_proof_reads.py:73](../../services/api/tests/visits/test_proof_reads.py#L73) |
| test_read_url_is_signed_expiring_and_not_an_upload_link | [services/api/tests/visits/test_proof_reads.py:104](../../services/api/tests/visits/test_proof_reads.py#L104) |
| test_an_unconfirmed_upload_is_not_shown_to_the_customer | [services/api/tests/visits/test_proof_reads.py:120](../../services/api/tests/visits/test_proof_reads.py#L120) |
| test_upload_for_a_closed_job_is_refused | [services/api/tests/visits/test_proof_reads.py:136](../../services/api/tests/visits/test_proof_reads.py#L136) |
| test_history_and_today_carry_finish_time_rating_and_counts | [services/api/tests/visits/test_proof_reads.py:148](../../services/api/tests/visits/test_proof_reads.py#L148) |
| test_another_customers_visit_proof_is_not_readable | [services/api/tests/visits/test_proof_reads.py:175](../../services/api/tests/visits/test_proof_reads.py#L175) |
| test_vehicle_photo_shows_on_the_crew_card_and_customer_vehicle | [services/api/tests/visits/test_proof_reads.py:187](../../services/api/tests/visits/test_proof_reads.py#L187) |
| test_profile_photo_has_a_read_url | [services/api/tests/visits/test_proof_reads.py:211](../../services/api/tests/visits/test_proof_reads.py#L211) |
| test_login_sets_the_cookies_and_returns_the_profile | [services/api/tests/webauth/test_webauth.py:35](../../services/api/tests/webauth/test_webauth.py#L35) |
| test_me_reads_the_cookie_session | [services/api/tests/webauth/test_webauth.py:51](../../services/api/tests/webauth/test_webauth.py#L51) |
| test_a_change_by_cookie_needs_the_csrf_header | [services/api/tests/webauth/test_webauth.py:59](../../services/api/tests/webauth/test_webauth.py#L59) |
| test_a_matching_csrf_header_is_accepted | [services/api/tests/webauth/test_webauth.py:71](../../services/api/tests/webauth/test_webauth.py#L71) |
| test_a_csrf_value_from_another_session_is_refused | [services/api/tests/webauth/test_webauth.py:76](../../services/api/tests/webauth/test_webauth.py#L76) |
| test_logout_ends_the_session | [services/api/tests/webauth/test_webauth.py:85](../../services/api/tests/webauth/test_webauth.py#L85) |
| test_logout_without_a_session_just_clears | [services/api/tests/webauth/test_webauth.py:97](../../services/api/tests/webauth/test_webauth.py#L97) |
| test_five_wrong_passwords_lock_the_admin | [services/api/tests/webauth/test_webauth.py:101](../../services/api/tests/webauth/test_webauth.py#L101) |
| test_crew_and_customers_cannot_sign_in_to_the_portal | [services/api/tests/webauth/test_webauth.py:110](../../services/api/tests/webauth/test_webauth.py#L110) |
| test_bearer_tokens_still_work_without_csrf | [services/api/tests/webauth/test_webauth.py:117](../../services/api/tests/webauth/test_webauth.py#L117) |
| test_a_crew_token_is_refused_on_admin_routes | [services/api/tests/webauth/test_webauth.py:127](../../services/api/tests/webauth/test_webauth.py#L127) |
| test_a_crew_token_in_the_cookie_is_refused_too | [services/api/tests/webauth/test_webauth.py:136](../../services/api/tests/webauth/test_webauth.py#L136) |
| test_portal_pages_fall_back_to_index | [services/api/tests/webauth/test_webauth.py:155](../../services/api/tests/webauth/test_webauth.py#L155) |
| test_portal_files_are_served_and_cached | [services/api/tests/webauth/test_webauth.py:163](../../services/api/tests/webauth/test_webauth.py#L163) |
| test_portal_missing_file_is_404_not_index | [services/api/tests/webauth/test_webauth.py:169](../../services/api/tests/webauth/test_webauth.py#L169) |
| test_portal_cannot_escape_its_folder | [services/api/tests/webauth/test_webauth.py:173](../../services/api/tests/webauth/test_webauth.py#L173) |
| test_portal_not_built | [services/api/tests/webauth/test_webauth.py:179](../../services/api/tests/webauth/test_webauth.py#L179) |
| feedback tab follows a post-onboarding customer onto detail routes | [apps/mobile/test/customer_test.dart:43](../../apps/mobile/test/customer_test.dart#L43) |
| shows the first vehicle and its service details | [apps/mobile/test/customer_test.dart:53](../../apps/mobile/test/customer_test.dart#L53) |
| swiping selects the next vehicle | [apps/mobile/test/customer_test.dart:65](../../apps/mobile/test/customer_test.dart#L65) |
| the selection is kept when Home is opened again | [apps/mobile/test/customer_test.dart:91](../../apps/mobile/test/customer_test.dart#L91) |
| cutoff times are every half hour of the day | [apps/mobile/test/customer_test.dart:105](../../apps/mobile/test/customer_test.dart#L105) |
| splash end state | [apps/mobile/test/golden_test.dart:63](../../apps/mobile/test/golden_test.dart#L63) |
| login | [apps/mobile/test/golden_test.dart:73](../../apps/mobile/test/golden_test.dart#L73) |
| onboarding review | [apps/mobile/test/golden_test.dart:83](../../apps/mobile/test/golden_test.dart#L83) |
| $role home | [apps/mobile/test/golden_test.dart:105](../../apps/mobile/test/golden_test.dart#L105) |
| wrong password gives the API message | [apps/mobile/test/live_api_test.dart:42](../../apps/mobile/test/live_api_test.dart#L42) |
| customer | [apps/mobile/test/live_api_test.dart:50](../../apps/mobile/test/live_api_test.dart#L50) |
| crew | [apps/mobile/test/live_api_test.dart:56](../../apps/mobile/test/live_api_test.dart#L56) |
| admin | [apps/mobile/test/live_api_test.dart:60](../../apps/mobile/test/live_api_test.dart#L60) |
| a role cannot read another role home | [apps/mobile/test/live_api_test.dart:66](../../apps/mobile/test/live_api_test.dart#L66) |
| splash goes to login when signed out | [apps/mobile/test/screens_test.dart:24](../../apps/mobile/test/screens_test.dart#L24) |
| splash with reduce motion is short | [apps/mobile/test/screens_test.dart:31](../../apps/mobile/test/screens_test.dart#L31) |
| wrong password shows the API message | [apps/mobile/test/screens_test.dart:41](../../apps/mobile/test/screens_test.dart#L41) |
| empty fields are checked before calling the API | [apps/mobile/test/screens_test.dart:49](../../apps/mobile/test/screens_test.dart#L49) |
| an email that is not registered shows the API message | [apps/mobile/test/screens_test.dart:70](../../apps/mobile/test/screens_test.dart#L70) |
| first sign-in: code, then a password, then home | [apps/mobile/test/screens_test.dart:79](../../apps/mobile/test/screens_test.dart#L79) |
| the code can be sent again when the countdown ends | [apps/mobile/test/screens_test.dart:120](../../apps/mobile/test/screens_test.dart#L120) |
| forgot password sends a code | [apps/mobile/test/screens_test.dart:136](../../apps/mobile/test/screens_test.dart#L136) |
| customer login lands on the customer home | [apps/mobile/test/screens_test.dart:151](../../apps/mobile/test/screens_test.dart#L151) |
| crew login lands on the crew home | [apps/mobile/test/screens_test.dart:177](../../apps/mobile/test/screens_test.dart#L177) |
| admin login lands on the admin home | [apps/mobile/test/screens_test.dart:186](../../apps/mobile/test/screens_test.dart#L186) |
| a stored session skips login and sign out returns to it | [apps/mobile/test/screens_test.dart:195](../../apps/mobile/test/screens_test.dart#L195) |
| admin signs out of all devices after confirming | [apps/mobile/test/screens_test.dart:211](../../apps/mobile/test/screens_test.dart#L211) |
| demo accounts fill the ID field in dev builds | [apps/mobile/test/screens_test.dart:236](../../apps/mobile/test/screens_test.dart#L236) |
| dark theme renders the login screen | [apps/mobile/test/screens_test.dart:244](../../apps/mobile/test/screens_test.dart#L244) |
| dates are dd-Mon-yy | [apps/mobile/test/unit_test.dart:11](../../apps/mobile/test/unit_test.dart#L11) |
| rupees use Indian grouping | [apps/mobile/test/unit_test.dart:14](../../apps/mobile/test/unit_test.dart#L14) |
| round-trips through JSON | [apps/mobile/test/unit_test.dart:21](../../apps/mobile/test/unit_test.dart#L21) |
| unknown role falls back to customer, home path follows role | [apps/mobile/test/unit_test.dart:26](../../apps/mobile/test/unit_test.dart#L26) |
| memory store keeps and clears a session | [apps/mobile/test/unit_test.dart:30](../../apps/mobile/test/unit_test.dart#L30) |
| signed-out user goes to login | [apps/mobile/test/unit_test.dart:40](../../apps/mobile/test/unit_test.dart#L40) |
| signed-in user is kept in their own role shell | [apps/mobile/test/unit_test.dart:44](../../apps/mobile/test/unit_test.dart#L44) |
| the splash is never redirected | [apps/mobile/test/unit_test.dart:51](../../apps/mobile/test/unit_test.dart#L51) |
| customer home | [apps/mobile/test/unit_test.dart:57](../../apps/mobile/test/unit_test.dart#L57) |
| shows real counts and a payment to confirm | [apps/mobile/test/admin_quick/admin_quick_test.dart:316](../../apps/mobile/test/admin_quick/admin_quick_test.dart#L316) |
| opens every quick action | [apps/mobile/test/admin_quick/admin_quick_test.dart:324](../../apps/mobile/test/admin_quick/admin_quick_test.dart#L324) |
| filters by status | [apps/mobile/test/admin_quick/admin_quick_test.dart:346](../../apps/mobile/test/admin_quick/admin_quick_test.dart#L346) |
| changes the status with a note | [apps/mobile/test/admin_quick/admin_quick_test.dart:362](../../apps/mobile/test/admin_quick/admin_quick_test.dart#L362) |
| adds a note, and asks for text first | [apps/mobile/test/admin_quick/admin_quick_test.dart:381](../../apps/mobile/test/admin_quick/admin_quick_test.dart#L381) |
| shows the server message when a save fails | [apps/mobile/test/admin_quick/admin_quick_test.dart:394](../../apps/mobile/test/admin_quick/admin_quick_test.dart#L394) |
| shows the average and filters by rating | [apps/mobile/test/admin_quick/admin_quick_test.dart:404](../../apps/mobile/test/admin_quick/admin_quick_test.dart#L404) |
| the day groups jobs by crew and moves by a day | [apps/mobile/test/admin_quick/admin_quick_test.dart:417](../../apps/mobile/test/admin_quick/admin_quick_test.dart#L417) |
| capacity starts on a Sunday and marks over capacity days | [apps/mobile/test/admin_quick/admin_quick_test.dart:434](../../apps/mobile/test/admin_quick/admin_quick_test.dart#L434) |
| the ARB fragment has the same keys and words as the code | [apps/mobile/test/admin_quick/admin_quick_test.dart:447](../../apps/mobile/test/admin_quick/admin_quick_test.dart#L447) |
| missed Interior is retried only through the next-day action | [apps/mobile/test/admin_quick/operations_actions_test.dart:180](../../apps/mobile/test/admin_quick/operations_actions_test.dart#L180) |
| Exterior offers the extension skip and no retry | [apps/mobile/test/admin_quick/operations_actions_test.dart:200](../../apps/mobile/test/admin_quick/operations_actions_test.dart#L200) |
| server rejection is visible to the admin | [apps/mobile/test/admin_quick/operations_actions_test.dart:211](../../apps/mobile/test/admin_quick/operations_actions_test.dart#L211) |
| customer quick actions use the existing skip and end-pause APIs | [apps/mobile/test/admin_quick/operations_actions_test.dart:218](../../apps/mobile/test/admin_quick/operations_actions_test.dart#L218) |
| crew exception uses the selected type and range | [apps/mobile/test/admin_quick/operations_actions_test.dart:238](../../apps/mobile/test/admin_quick/operations_actions_test.dart#L238) |
| add-on requests are read only and show assignment and payment | [apps/mobile/test/admin_quick/operations_actions_test.dart:255](../../apps/mobile/test/admin_quick/operations_actions_test.dart#L255) |
| the welcome screen has two buttons that open the email screen | [apps/mobile/test/auth/auth_entry_test.dart:53](../../apps/mobile/test/auth/auth_entry_test.dart#L53) |
| already a member also opens the email screen | [apps/mobile/test/auth/auth_entry_test.dart:63](../../apps/mobile/test/auth/auth_entry_test.dart#L63) |
| an email with a bad format shows an error | [apps/mobile/test/auth/auth_entry_test.dart:70](../../apps/mobile/test/auth/auth_entry_test.dart#L70) |
| not registered shows the support buttons | [apps/mobile/test/auth/auth_entry_test.dart:80](../../apps/mobile/test/auth/auth_entry_test.dart#L80) |
| the Terms and Privacy Policy words open links | [apps/mobile/test/auth/auth_entry_test.dart:95](../../apps/mobile/test/auth/auth_entry_test.dart#L95) |
| the ARB fragment has the same keys and words as the code | [apps/mobile/test/auth/auth_entry_test.dart:115](../../apps/mobile/test/auth/auth_entry_test.dart#L115) |
| late refresh ${fail ?  | [apps/mobile/test/auth/refresh_account_switch_test.dart:24](../../apps/mobile/test/auth/refresh_account_switch_test.dart#L24) |
| late refresh cannot restore a signed-out account | [apps/mobile/test/auth/refresh_account_switch_test.dart:48](../../apps/mobile/test/auth/refresh_account_switch_test.dart#L48) |
| payment QR encodes the backend amount and submitted page shows preferences | [apps/mobile/test/changes_money/changes_money_test.dart:14](../../apps/mobile/test/changes_money/changes_money_test.dart#L14) |
| payment instructions preserve the server amount-bearing QR payload | [apps/mobile/test/changes_money/changes_money_test.dart:25](../../apps/mobile/test/changes_money/changes_money_test.dart#L25) |
| payment status labels follow PAY-09 | [apps/mobile/test/changes_money/changes_money_test.dart:32](../../apps/mobile/test/changes_money/changes_money_test.dart#L32) |
| finish-by times are in 30-minute steps | [apps/mobile/test/changes_money/changes_money_test.dart:39](../../apps/mobile/test/changes_money/changes_money_test.dart#L39) |
| a subscription reads from the API shape | [apps/mobile/test/changes_money/changes_money_test.dart:47](../../apps/mobile/test/changes_money/changes_money_test.dart#L47) |
| route paths | [apps/mobile/test/changes_money/changes_money_test.dart:70](../../apps/mobile/test/changes_money/changes_money_test.dart#L70) |
| skip with no date says to pick one first | [apps/mobile/test/changes_money/changes_money_test.dart:78](../../apps/mobile/test/changes_money/changes_money_test.dart#L78) |
| skip a date, with the note and a confirmation | [apps/mobile/test/changes_money/changes_money_test.dart:87](../../apps/mobile/test/changes_money/changes_money_test.dart#L87) |
| a skipped date can be undone | [apps/mobile/test/changes_money/changes_money_test.dart:100](../../apps/mobile/test/changes_money/changes_money_test.dart#L100) |
| a date past its 9 PM cutoff cannot be picked | [apps/mobile/test/changes_money/changes_money_test.dart:111](../../apps/mobile/test/changes_money/changes_money_test.dart#L111) |
| the server | [apps/mobile/test/changes_money/changes_money_test.dart:121](../../apps/mobile/test/changes_money/changes_money_test.dart#L121) |
| pause needs both dates | [apps/mobile/test/changes_money/changes_money_test.dart:132](../../apps/mobile/test/changes_money/changes_money_test.dart#L132) |
| a running pause can be ended | [apps/mobile/test/changes_money/changes_money_test.dart:143](../../apps/mobile/test/changes_money/changes_money_test.dart#L143) |
| My subscription shows the cycle and the latest payment | [apps/mobile/test/changes_money/changes_money_test.dart:165](../../apps/mobile/test/changes_money/changes_money_test.dart#L165) |
| pay for next month opens the UPI screen | [apps/mobile/test/changes_money/changes_money_test.dart:176](../../apps/mobile/test/changes_money/changes_money_test.dart#L176) |
| no pay button when the payment is not open | [apps/mobile/test/changes_money/changes_money_test.dart:186](../../apps/mobile/test/changes_money/changes_money_test.dart#L186) |
| billing history lists newest first with an invoice | [apps/mobile/test/changes_money/changes_money_test.dart:202](../../apps/mobile/test/changes_money/changes_money_test.dart#L202) |
| I | [apps/mobile/test/changes_money/changes_money_test.dart:214](../../apps/mobile/test/changes_money/changes_money_test.dart#L214) |
| a date is required before Confirm & pay | [apps/mobile/test/changes_money/changes_money_test.dart:232](../../apps/mobile/test/changes_money/changes_money_test.dart#L232) |
| earlier requests show their status and can be cancelled | [apps/mobile/test/changes_money/changes_money_test.dart:243](../../apps/mobile/test/changes_money/changes_money_test.dart#L243) |
| standalone Spa reuses the priced booking form and requires a date | [apps/mobile/test/changes_money/changes_money_test.dart:261](../../apps/mobile/test/changes_money/changes_money_test.dart#L261) |
| standalone confirmation opens the Spa UPI payment | [apps/mobile/test/changes_money/changes_money_test.dart:271](../../apps/mobile/test/changes_money/changes_money_test.dart#L271) |
| confirm a payment | [apps/mobile/test/changes_money/changes_money_test.dart:287](../../apps/mobile/test/changes_money/changes_money_test.dart#L287) |
| reject sends the payment back | [apps/mobile/test/changes_money/changes_money_test.dart:298](../../apps/mobile/test/changes_money/changes_money_test.dart#L298) |
| alerts can be marked read | [apps/mobile/test/changes_money/changes_money_test.dart:306](../../apps/mobile/test/changes_money/changes_money_test.dart#L306) |
| PDF requests use the authenticated API and preserve binary bytes | [apps/mobile/test/changes_money/invoice_pdf_test.dart:56](../../apps/mobile/test/changes_money/invoice_pdf_test.dart#L56) |
| non-PDF success responses are rejected instead of passed to the renderer | [apps/mobile/test/changes_money/invoice_pdf_test.dart:67](../../apps/mobile/test/changes_money/invoice_pdf_test.dart#L67) |
| binary JSON errors retain the backend message and status | [apps/mobile/test/changes_money/invoice_pdf_test.dart:72](../../apps/mobile/test/changes_money/invoice_pdf_test.dart#L72) |
| invoice summary opens the PDF without adding save/share actions | [apps/mobile/test/changes_money/invoice_pdf_test.dart:79](../../apps/mobile/test/changes_money/invoice_pdf_test.dart#L79) |
| PDF errors offer retry and reload after recovery | [apps/mobile/test/changes_money/invoice_pdf_test.dart:90](../../apps/mobile/test/changes_money/invoice_pdf_test.dart#L90) |
| capture enforces strict ${video ?  | [apps/mobile/test/crew/models_test.dart:10](../../apps/mobile/test/crew/models_test.dart#L10) |
| a visit list maps the cards and the counts | [apps/mobile/test/crew/models_test.dart:18](../../apps/mobile/test/crew/models_test.dart#L18) |
| a visit list for all jobs has no date | [apps/mobile/test/crew/models_test.dart:41](../../apps/mobile/test/crew/models_test.dart#L41) |
| a job detail maps the checklist, the proof and the outcome | [apps/mobile/test/crew/models_test.dart:54](../../apps/mobile/test/crew/models_test.dart#L54) |
| the profile knows a Manager | [apps/mobile/test/crew/models_test.dart:90](../../apps/mobile/test/crew/models_test.dart#L90) |
| dates are sent as yyyy-mm-dd | [apps/mobile/test/crew/models_test.dart:106](../../apps/mobile/test/crew/models_test.dart#L106) |
| accepts camera formats, including iPhone HEIC | [apps/mobile/test/crew/models_test.dart:112](../../apps/mobile/test/crew/models_test.dart#L112) |
| rejects other formats | [apps/mobile/test/crew/models_test.dart:119](../../apps/mobile/test/crew/models_test.dart#L119) |
| photos are under 10 MB and videos under 25 MB | [apps/mobile/test/crew/models_test.dart:125](../../apps/mobile/test/crew/models_test.dart#L125) |
| reopened queue adapters retain only their own uploads and quarantine legacy rows | [apps/mobile/test/crew/queue_store_test.dart:60](../../apps/mobile/test/crew/queue_store_test.dart#L60) |
| queue identity is stable across token refresh and distinct across logins | [apps/mobile/test/crew/queue_store_test.dart:80](../../apps/mobile/test/crew/queue_store_test.dart#L80) |
| account queues ignore other owners and unknown legacy records | [apps/mobile/test/crew/queue_test.dart:69](../../apps/mobile/test/crew/queue_test.dart#L69) |
| account switch stops after in-flight request and resumes for original owner | [apps/mobile/test/crew/queue_test.dart:84](../../apps/mobile/test/crew/queue_test.dart#L84) |
| signed-out immediate upload cannot reach the API | [apps/mobile/test/crew/queue_test.dart:109](../../apps/mobile/test/crew/queue_test.dart#L109) |
| a queued file is requested, sent and confirmed, then removed | [apps/mobile/test/crew/queue_test.dart:118](../../apps/mobile/test/crew/queue_test.dart#L118) |
| with no connection the file stays and goes out when it returns | [apps/mobile/test/crew/queue_test.dart:141](../../apps/mobile/test/crew/queue_test.dart#L141) |
| after the app closes, the queue resumes at the saved step | [apps/mobile/test/crew/queue_test.dart:163](../../apps/mobile/test/crew/queue_test.dart#L163) |
| a file that was requested but not sent is sent on resume without a  | [apps/mobile/test/crew/queue_test.dart:186](../../apps/mobile/test/crew/queue_test.dart#L186) |
| an expired link (403) asks for a new one | [apps/mobile/test/crew/queue_test.dart:206](../../apps/mobile/test/crew/queue_test.dart#L206) |
| a rejected file is parked as failed, and retry puts it back | [apps/mobile/test/crew/queue_test.dart:223](../../apps/mobile/test/crew/queue_test.dart#L223) |
| repeated server errors park the file after the attempt limit | [apps/mobile/test/crew/queue_test.dart:240](../../apps/mobile/test/crew/queue_test.dart#L240) |
| waitingFor counts the files of one job | [apps/mobile/test/crew/queue_test.dart:254](../../apps/mobile/test/crew/queue_test.dart#L254) |
| queued rows round trip through the database mapping | [apps/mobile/test/crew/queue_test.dart:265](../../apps/mobile/test/crew/queue_test.dart#L265) |
| the home shows today\ | [apps/mobile/test/crew/screens_test.dart:25](../../apps/mobile/test/crew/screens_test.dart#L25) |
| the day can be moved and all jobs shown | [apps/mobile/test/crew/screens_test.dart:40](../../apps/mobile/test/crew/screens_test.dart#L40) |
| a job cannot be marked complete until the checklist and proof  | [apps/mobile/test/crew/screens_test.dart:55](../../apps/mobile/test/crew/screens_test.dart#L55) |
| with no connection the photo waits and completion stays off | [apps/mobile/test/crew/screens_test.dart:91](../../apps/mobile/test/crew/screens_test.dart#L91) |
| a file that breaks the rules is not queued | [apps/mobile/test/crew/screens_test.dart:119](../../apps/mobile/test/crew/screens_test.dart#L119) |
| could not complete needs a reason and records it | [apps/mobile/test/crew/screens_test.dart:138](../../apps/mobile/test/crew/screens_test.dart#L138) |
| a Manager sees the team and can reassign and skip a job | [apps/mobile/test/crew/screens_test.dart:166](../../apps/mobile/test/crew/screens_test.dart#L166) |
| a Manager marks a crew member absent and sees the jobs moved | [apps/mobile/test/crew/screens_test.dart:196](../../apps/mobile/test/crew/screens_test.dart#L196) |
| a Manager changes working hours for a crew member | [apps/mobile/test/crew/screens_test.dart:216](../../apps/mobile/test/crew/screens_test.dart#L216) |
| reassign shows why a crew member cannot take the job | [apps/mobile/test/crew/screens_test.dart:241](../../apps/mobile/test/crew/screens_test.dart#L241) |
| a Member has no team button | [apps/mobile/test/crew/screens_test.dart:261](../../apps/mobile/test/crew/screens_test.dart#L261) |
| the profile shows the crew member\ | [apps/mobile/test/crew/screens_test.dart:267](../../apps/mobile/test/crew/screens_test.dart#L267) |
| edit profile saves names and mobile (ACC-06) | [apps/mobile/test/customer/account_test.dart:166](../../apps/mobile/test/customer/account_test.dart#L166) |
| change email asks for the code, then verifies (ACC-08) | [apps/mobile/test/customer/account_test.dart:200](../../apps/mobile/test/customer/account_test.dart#L200) |
| the vehicle photo is added through the camera (VEH-01) | [apps/mobile/test/customer/account_test.dart:220](../../apps/mobile/test/customer/account_test.dart#L220) |
| a photo in a format that is not accepted is refused | [apps/mobile/test/customer/account_test.dart:238](../../apps/mobile/test/customer/account_test.dart#L238) |
| report an issue sends the attached photos and the visit | [apps/mobile/test/customer/account_test.dart:263](../../apps/mobile/test/customer/account_test.dart#L263) |
| adds a vehicle in a chosen society, requires a photo and opens its first payment | [apps/mobile/test/customer/add_vehicle_test.dart:178](../../apps/mobile/test/customer/add_vehicle_test.dart#L178) |
| empty societies block adding a vehicle and explain availability | [apps/mobile/test/customer/add_vehicle_test.dart:216](../../apps/mobile/test/customer/add_vehicle_test.dart#L216) |
| admin mobile displays the five-step list without editing controls | [apps/mobile/test/customer/admin_checklists_test.dart:7](../../apps/mobile/test/customer/admin_checklists_test.dart#L7) |
| a projected day is expected and can be skipped | [apps/mobile/test/customer/calendar_home_test.dart:173](../../apps/mobile/test/customer/calendar_home_test.dart#L173) |
| change cutoff time picks a time and sends it | [apps/mobile/test/customer/calendar_home_test.dart:195](../../apps/mobile/test/customer/calendar_home_test.dart#L195) |
| a skipped day with a skip can be undone | [apps/mobile/test/customer/calendar_home_test.dart:212](../../apps/mobile/test/customer/calendar_home_test.dart#L212) |
| after the cutoff the controls close and Call support opens  | [apps/mobile/test/customer/calendar_home_test.dart:227](../../apps/mobile/test/customer/calendar_home_test.dart#L227) |
| a requested change keeps the value and says it is waiting | [apps/mobile/test/customer/calendar_home_test.dart:248](../../apps/mobile/test/customer/calendar_home_test.dart#L248) |
| missed days say where the work was covered or rescheduled | [apps/mobile/test/customer/calendar_home_test.dart:274](../../apps/mobile/test/customer/calendar_home_test.dart#L274) |
| an assigned visit shows the crew member and time | [apps/mobile/test/customer/calendar_home_test.dart:307](../../apps/mobile/test/customer/calendar_home_test.dart#L307) |
| a paused day and the renewal date are shown | [apps/mobile/test/customer/calendar_home_test.dart:322](../../apps/mobile/test/customer/calendar_home_test.dart#L322) |
| markers: upcoming interior and spa days are outlined shapes | [apps/mobile/test/customer/calendar_home_test.dart:334](../../apps/mobile/test/customer/calendar_home_test.dart#L334) |
| greets by time of day and shows Tomorrow with the crew | [apps/mobile/test/customer/calendar_home_test.dart:365](../../apps/mobile/test/customer/calendar_home_test.dart#L365) |
| the evening greeting | [apps/mobile/test/customer/calendar_home_test.dart:380](../../apps/mobile/test/customer/calendar_home_test.dart#L380) |
| a due check-in shows a Monthly check-in card | [apps/mobile/test/customer/calendar_home_test.dart:390](../../apps/mobile/test/customer/calendar_home_test.dart#L390) |
| no check-in card when nothing is due | [apps/mobile/test/customer/calendar_home_test.dart:410](../../apps/mobile/test/customer/calendar_home_test.dart#L410) |
| the Add-ons card is only for an Active vehicle | [apps/mobile/test/customer/calendar_home_test.dart:420](../../apps/mobile/test/customer/calendar_home_test.dart#L420) |
| the Add-ons card is hidden without a subscription | [apps/mobile/test/customer/calendar_home_test.dart:432](../../apps/mobile/test/customer/calendar_home_test.dart#L432) |
| shows the month, markers and the day card of today | [apps/mobile/test/customer/customer_slice_test.dart:350](../../apps/mobile/test/customer/customer_slice_test.dart#L350) |
| a completed day opens the service details | [apps/mobile/test/customer/customer_slice_test.dart:374](../../apps/mobile/test/customer/customer_slice_test.dart#L374) |
| a skipped day and a day without a visit say so | [apps/mobile/test/customer/customer_slice_test.dart:389](../../apps/mobile/test/customer/customer_slice_test.dart#L389) |
| the arrows move between months | [apps/mobile/test/customer/customer_slice_test.dart:405](../../apps/mobile/test/customer/customer_slice_test.dart#L405) |
| a failed load can be retried | [apps/mobile/test/customer/customer_slice_test.dart:420](../../apps/mobile/test/customer/customer_slice_test.dart#L420) |
| lists the jobs and the photos, and opens the viewer | [apps/mobile/test/customer/customer_slice_test.dart:437](../../apps/mobile/test/customer/customer_slice_test.dart#L437) |
| lists visits and opens a completed one | [apps/mobile/test/customer/customer_slice_test.dart:456](../../apps/mobile/test/customer/customer_slice_test.dart#L456) |
| shows the crew card, checklist and AFTER label | [apps/mobile/test/customer/customer_slice_test.dart:472](../../apps/mobile/test/customer/customer_slice_test.dart#L472) |
| offers a rating | [apps/mobile/test/customer/customer_slice_test.dart:489](../../apps/mobile/test/customer/customer_slice_test.dart#L489) |
| shows the rating given | [apps/mobile/test/customer/customer_slice_test.dart:494](../../apps/mobile/test/customer/customer_slice_test.dart#L494) |
| opens the report form linked to the visit | [apps/mobile/test/customer/customer_slice_test.dart:505](../../apps/mobile/test/customer/customer_slice_test.dart#L505) |
| shows the summary and opens the proof | [apps/mobile/test/customer/customer_slice_test.dart:524](../../apps/mobile/test/customer/customer_slice_test.dart#L524) |
| shows nothing when no clean finished today | [apps/mobile/test/customer/customer_slice_test.dart:542](../../apps/mobile/test/customer/customer_slice_test.dart#L542) |
| lists vehicles and opens a vehicle | [apps/mobile/test/customer/customer_slice_test.dart:549](../../apps/mobile/test/customer/customer_slice_test.dart#L549) |
| shows the name, the unread count and signs out | [apps/mobile/test/customer/customer_slice_test.dart:566](../../apps/mobile/test/customer/customer_slice_test.dart#L566) |
| opens the vehicles list and the notifications | [apps/mobile/test/customer/customer_slice_test.dart:587](../../apps/mobile/test/customer/customer_slice_test.dart#L587) |
| a tap marks the message read and opens its visit | [apps/mobile/test/customer/customer_slice_test.dart:598](../../apps/mobile/test/customer/customer_slice_test.dart#L598) |
| mark all as read | [apps/mobile/test/customer/customer_slice_test.dart:610](../../apps/mobile/test/customer/customer_slice_test.dart#L610) |
| fills the card from the visits when Home has none | [apps/mobile/test/customer/customer_slice_test.dart:621](../../apps/mobile/test/customer/customer_slice_test.dart#L621) |
| routes list the slice pages | [apps/mobile/test/customer/customer_slice_test.dart:662](../../apps/mobile/test/customer/customer_slice_test.dart#L662) |
| confirmation opens the unpaid vehicle payment after saving the review | [apps/mobile/test/customer/onboarding_flow_test.dart:76](../../apps/mobile/test/customer/onboarding_flow_test.dart#L76) |
| an already received payment confirms directly to Home | [apps/mobile/test/customer/onboarding_flow_test.dart:84](../../apps/mobile/test/customer/onboarding_flow_test.dart#L84) |
| Back retains edits saved on Continue | [apps/mobile/test/customer/onboarding_flow_test.dart:93](../../apps/mobile/test/customer/onboarding_flow_test.dart#L93) |
| seven review steps save on Continue and put plan before preferences | [apps/mobile/test/customer/onboarding_flow_test.dart:103](../../apps/mobile/test/customer/onboarding_flow_test.dart#L103) |
| restored position opens the saved step and keeps read-only fields | [apps/mobile/test/customer/onboarding_flow_test.dart:128](../../apps/mobile/test/customer/onboarding_flow_test.dart#L128) |
| a failed draft save stays on the current step | [apps/mobile/test/customer/onboarding_flow_test.dart:135](../../apps/mobile/test/customer/onboarding_flow_test.dart#L135) |
| vehicle step cannot continue without its photo | [apps/mobile/test/customer/onboarding_flow_test.dart:142](../../apps/mobile/test/customer/onboarding_flow_test.dart#L142) |
| refresh keeps the original media ID when proof ordering changes | [apps/mobile/test/customer/proof_video_test.dart:76](../../apps/mobile/test/customer/proof_video_test.dart#L76) |
| plays and pauses in-app and seeks within the video | [apps/mobile/test/customer/proof_video_test.dart:84](../../apps/mobile/test/customer/proof_video_test.dart#L84) |
| expired URL retries through owned visit reads and replaces the player | [apps/mobile/test/customer/proof_video_test.dart:99](../../apps/mobile/test/customer/proof_video_test.dart#L99) |
| a removed video does not play a different proof item | [apps/mobile/test/customer/proof_video_test.dart:110](../../apps/mobile/test/customer/proof_video_test.dart#L110) |
| app backgrounding pauses playback | [apps/mobile/test/customer/proof_video_test.dart:121](../../apps/mobile/test/customer/proof_video_test.dart#L121) |
| disposing while loading cancels the timeout and releases resources | [apps/mobile/test/customer/proof_video_test.dart:129](../../apps/mobile/test/customer/proof_video_test.dart#L129) |
| open Home observes externally changed onboarding state on a refresh pulse | [apps/mobile/test/customer/read_refresh_test.dart:13](../../apps/mobile/test/customer/read_refresh_test.dart#L13) |
| refresh pauses in background and emits on resume | [apps/mobile/test/customer/read_refresh_test.dart:31](../../apps/mobile/test/customer/read_refresh_test.dart#L31) |
| verified RC stays verified and parking options come from its society | [apps/mobile/test/customer/screen_parity_test.dart:29](../../apps/mobile/test/customer/screen_parity_test.dart#L29) |
| completed calendar card includes finish time and checked count | [apps/mobile/test/customer/screen_parity_test.dart:40](../../apps/mobile/test/customer/screen_parity_test.dart#L40) |
| bundled FAQ parser keeps question order and the admin reactivation rule | [apps/mobile/test/customer/screen_parity_test.dart:49](../../apps/mobile/test/customer/screen_parity_test.dart#L49) |
| a visit, a payment, a complaint and the check-in | [apps/mobile/test/notifications/notifications_test.dart:144](../../apps/mobile/test/notifications/notifications_test.dart#L144) |
| shows one switch for each event, all on | [apps/mobile/test/notifications/notifications_test.dart:166](../../apps/mobile/test/notifications/notifications_test.dart#L166) |
| a switch is saved on its own | [apps/mobile/test/notifications/notifications_test.dart:179](../../apps/mobile/test/notifications/notifications_test.dart#L179) |
| registers the token of a signed-in customer | [apps/mobile/test/notifications/notifications_test.dart:213](../../apps/mobile/test/notifications/notifications_test.dart#L213) |
| does nothing without a token | [apps/mobile/test/notifications/notifications_test.dart:218](../../apps/mobile/test/notifications/notifications_test.dart#L218) |
| lists messages and marks all read | [apps/mobile/test/notifications/notifications_test.dart:225](../../apps/mobile/test/notifications/notifications_test.dart#L225) |
| a tap marks one read | [apps/mobile/test/notifications/notifications_test.dart:237](../../apps/mobile/test/notifications/notifications_test.dart#L237) |
| reads the API reply | [apps/mobile/test/people/people_test.dart:93](../../apps/mobile/test/people/people_test.dart#L93) |
| shows the profile, read only, with the hours | [apps/mobile/test/people/people_test.dart:100](../../apps/mobile/test/people/people_test.dart#L100) |
| says plainly when the crew record is missing | [apps/mobile/test/people/people_test.dart:114](../../apps/mobile/test/people/people_test.dart#L114) |
| lists every vehicle with its subscription status | [apps/mobile/test/people/people_test.dart:131](../../apps/mobile/test/people/people_test.dart#L131) |
| opens the details of a vehicle | [apps/mobile/test/people/people_test.dart:142](../../apps/mobile/test/people/people_test.dart#L142) |
| a vehicle without a subscription has no plan details | [apps/mobile/test/people/people_test.dart:154](../../apps/mobile/test/people/people_test.dart#L154) |
| a vehicle that is not on the account is said so | [apps/mobile/test/people/people_test.dart:162](../../apps/mobile/test/people/people_test.dart#L162) |
| lists the options and opens the dialer and WhatsApp | [apps/mobile/test/support/support_test.dart:35](../../apps/mobile/test/support/support_test.dart#L35) |
| shows the check-in when one is due | [apps/mobile/test/support/support_test.dart:53](../../apps/mobile/test/support/support_test.dart#L53) |
| give feedback opens the feedback sheet | [apps/mobile/test/support/support_test.dart:67](../../apps/mobile/test/support/support_test.dart#L67) |
| a failed load shows the retry view | [apps/mobile/test/support/support_test.dart:73](../../apps/mobile/test/support/support_test.dart#L73) |
| asks for a category and a description (ISS-05) | [apps/mobile/test/support/support_test.dart:81](../../apps/mobile/test/support/support_test.dart#L81) |
| sends the report and lands on My complaints (ISS-06) | [apps/mobile/test/support/support_test.dart:91](../../apps/mobile/test/support/support_test.dart#L91) |
| shows the server | [apps/mobile/test/support/support_test.dart:112](../../apps/mobile/test/support/support_test.dart#L112) |
| lists complaints with status and the latest note | [apps/mobile/test/support/support_test.dart:125](../../apps/mobile/test/support/support_test.dart#L125) |
| says so when there are none | [apps/mobile/test/support/support_test.dart:144](../../apps/mobile/test/support/support_test.dart#L144) |
| shows the thread and sends a reply | [apps/mobile/test/support/support_test.dart:149](../../apps/mobile/test/support/support_test.dart#L149) |
| a resolved complaint has no reply box | [apps/mobile/test/support/support_test.dart:178](../../apps/mobile/test/support/support_test.dart#L178) |
| Send needs a rating or a comment, not a category alone | [apps/mobile/test/support/support_test.dart:199](../../apps/mobile/test/support/support_test.dart#L199) |
| sends with the testimonial box off unless ticked | [apps/mobile/test/support/support_test.dart:211](../../apps/mobile/test/support/support_test.dart#L211) |
| a comment alone can be sent, with permission | [apps/mobile/test/support/support_test.dart:222](../../apps/mobile/test/support/support_test.dart#L222) |
| 5 stars offers the positive tags | [apps/mobile/test/support/support_test.dart:245](../../apps/mobile/test/support/support_test.dart#L245) |
| fewer than 5 stars offers the issue tags, and clears the rest | [apps/mobile/test/support/support_test.dart:261](../../apps/mobile/test/support/support_test.dart#L261) |
| needs one rating, then saves and says thank you | [apps/mobile/test/support/support_test.dart:281](../../apps/mobile/test/support/support_test.dart#L281) |
| tapping the same star again leaves the category unrated | [apps/mobile/test/support/support_test.dart:306](../../apps/mobile/test/support/support_test.dart#L306) |
| says so when nothing is due | [apps/mobile/test/support/support_test.dart:315](../../apps/mobile/test/support/support_test.dart#L315) |
| lists alerts with the unread count and marks one read | [apps/mobile/test/support/support_test.dart:335](../../apps/mobile/test/support/support_test.dart#L335) |
| marks all as read | [apps/mobile/test/support/support_test.dart:348](../../apps/mobile/test/support/support_test.dart#L348) |
| says so when there are none | [apps/mobile/test/support/support_test.dart:358](../../apps/mobile/test/support/support_test.dart#L358) |
| the ARB fragment has the same keys and words as the code | [apps/mobile/test/support/support_test.dart:365](../../apps/mobile/test/support/support_test.dart#L365) |
| complaint JSON and progress step | [apps/mobile/test/support/support_test.dart:377](../../apps/mobile/test/support/support_test.dart#L377) |
| whatsapp link keeps only the digits | [apps/mobile/test/support/support_test.dart:402](../../apps/mobile/test/support/support_test.dart#L402) |
| Help lists the FAQ and its questions expand (SUP-01, SUP-05) | [apps/mobile/test/support/wp8_test.dart:33](../../apps/mobile/test/support/wp8_test.dart#L33) |
| the feedback tab opens feedback and moves along the edge (FDBK-01) | [apps/mobile/test/support/wp8_test.dart:76](../../apps/mobile/test/support/wp8_test.dart#L76) |
| the invoice page copies and emails the invoice (SUB-12) | [apps/mobile/test/support/wp8_test.dart:104](../../apps/mobile/test/support/wp8_test.dart#L104) |
| each role signs in, sees its home and signs out | [apps/mobile/integration_test/logins_test.dart:39](../../apps/mobile/integration_test/logins_test.dart#L39) |
| sends a signed-out visitor to the sign-in page | [apps/web/src/App.test.tsx:45](../../apps/web/src/App.test.tsx#L45) |
| shows the navigation and the page when signed in | [apps/web/src/App.test.tsx:52](../../apps/web/src/App.test.tsx#L52) |
| signs in and lands on the page that was asked for | [apps/web/src/App.test.tsx:63](../../apps/web/src/App.test.tsx#L63) |
| shows the API | [apps/web/src/App.test.tsx:78](../../apps/web/src/App.test.tsx#L78) |
| signs out and returns to sign-in | [apps/web/src/App.test.tsx:93](../../apps/web/src/App.test.tsx#L93) |
| finds a cookie by name | [apps/web/src/api/client.test.ts:24](../../apps/web/src/api/client.test.ts#L24) |
| sends credentials and no CSRF header on a read | [apps/web/src/api/client.test.ts:31](../../apps/web/src/api/client.test.ts#L31) |
| adds the CSRF header on a change | [apps/web/src/api/client.test.ts:40](../../apps/web/src/api/client.test.ts#L40) |
| sends a JSON body | [apps/web/src/api/client.test.ts:46](../../apps/web/src/api/client.test.ts#L46) |
| turns the error envelope into an ApiError | [apps/web/src/api/client.test.ts:54](../../apps/web/src/api/client.test.ts#L54) |
| handles a reply that is not the envelope | [apps/web/src/api/client.test.ts:66](../../apps/web/src/api/client.test.ts#L66) |
| reports a network failure | [apps/web/src/api/client.test.ts:72](../../apps/web/src/api/client.test.ts#L72) |
| tells the listener about a 401, unless quiet | [apps/web/src/api/client.test.ts:77](../../apps/web/src/api/client.test.ts#L77) |
| Button is disabled while busy | [apps/web/src/components/components.test.tsx:9](../../apps/web/src/components/components.test.tsx#L9) |
| TextField links its label and error | [apps/web/src/components/components.test.tsx:14](../../apps/web/src/components/components.test.tsx#L14) |
| Table renders rows and an empty message | [apps/web/src/components/components.test.tsx:21](../../apps/web/src/components/components.test.tsx#L21) |
| StatusChip shows its label | [apps/web/src/components/components.test.tsx:30](../../apps/web/src/components/components.test.tsx#L30) |
| Dialog closes on Escape | [apps/web/src/components/components.test.tsx:35](../../apps/web/src/components/components.test.tsx#L35) |
| Dialog keeps focus on the field being typed in when the parent re-renders | [apps/web/src/components/components.test.tsx:43](../../apps/web/src/components/components.test.tsx#L43) |
| Toast shows a message | [apps/web/src/components/components.test.tsx:61](../../apps/web/src/components/components.test.tsx#L61) |
| shows the real assignment and unpaid payment, and resolves a pending change | [apps/web/src/pages/addons/AddonsPage.test.tsx:29](../../apps/web/src/pages/addons/AddonsPage.test.tsx#L29) |
| filters by society and cancels only the selected booking | [apps/web/src/pages/addons/AddonsPage.test.tsx:38](../../apps/web/src/pages/addons/AddonsPage.test.tsx#L38) |
| filters by role and search, and asks the API for a society | [apps/web/src/pages/crew/crew.test.tsx:53](../../apps/web/src/pages/crew/crew.test.tsx#L53) |
| onboards a Trainee with a paired Member and shows the password once | [apps/web/src/pages/crew/crew.test.tsx:72](../../apps/web/src/pages/crew/crew.test.tsx#L72) |
| asks to release jobs when deactivation is blocked, then retries | [apps/web/src/pages/crew/crew.test.tsx:120](../../apps/web/src/pages/crew/crew.test.tsx#L120) |
| adds a Late start range with a start time | [apps/web/src/pages/crew/crew.test.tsx:144](../../apps/web/src/pages/crew/crew.test.tsx#L144) |
| resets a password and shows it once, and signs a session out | [apps/web/src/pages/crew/crew.test.tsx:164](../../apps/web/src/pages/crew/crew.test.tsx#L164) |
| changes a role to Trainee with a Member and lists released jobs | [apps/web/src/pages/crew/crew.test.tsx:187](../../apps/web/src/pages/crew/crew.test.tsx#L187) |
| clears start and end on a day off | [apps/web/src/pages/crew/crew.test.tsx:213](../../apps/web/src/pages/crew/crew.test.tsx#L213) |
| pages customer search and resets the offset when the search changes | [apps/web/src/pages/customers/customers.test.tsx:44](../../apps/web/src/pages/customers/customers.test.tsx#L44) |
| shows imported Spa history without inventing completion or a date | [apps/web/src/pages/customers/customers.test.tsx:62](../../apps/web/src/pages/customers/customers.test.tsx#L62) |
| searches customers through the server and opens their onboarding state | [apps/web/src/pages/customers/customers.test.tsx:75](../../apps/web/src/pages/customers/customers.test.tsx#L75) |
| changes to an exterior-only plan without submitting the old interior day | [apps/web/src/pages/customers/customers.test.tsx:103](../../apps/web/src/pages/customers/customers.test.tsx#L103) |
| resolves missed Interior work through the next-day-only action | [apps/web/src/pages/operations/OperationsPage.test.tsx:27](../../apps/web/src/pages/operations/OperationsPage.test.tsx#L27) |
| keeps Exterior coverage automatic and shows the skip extension | [apps/web/src/pages/operations/OperationsPage.test.tsx:34](../../apps/web/src/pages/operations/OperationsPage.test.tsx#L34) |
| filters the server queue by society and failure reason | [apps/web/src/pages/operations/OperationsPage.test.tsx:42](../../apps/web/src/pages/operations/OperationsPage.test.tsx#L42) |
| pages payments and resets the page on filter application | [apps/web/src/pages/payments/PaymentsPage.test.tsx:56](../../apps/web/src/pages/payments/PaymentsPage.test.tsx#L56) |
| lists payments and sends the filters | [apps/web/src/pages/payments/PaymentsPage.test.tsx:73](../../apps/web/src/pages/payments/PaymentsPage.test.tsx#L73) |
| confirms an Initiated payment | [apps/web/src/pages/payments/PaymentsPage.test.tsx:89](../../apps/web/src/pages/payments/PaymentsPage.test.tsx#L89) |
| offers reject only for Initiated or Received and no confirm for Received | [apps/web/src/pages/payments/PaymentsPage.test.tsx:100](../../apps/web/src/pages/payments/PaymentsPage.test.tsx#L100) |
| sets a status with the chosen value | [apps/web/src/pages/payments/PaymentsPage.test.tsx:108](../../apps/web/src/pages/payments/PaymentsPage.test.tsx#L108) |
| shows the error message from the API | [apps/web/src/pages/payments/PaymentsPage.test.tsx:122](../../apps/web/src/pages/payments/PaymentsPage.test.tsx#L122) |
| issues an invoice for a Received payment | [apps/web/src/pages/payments/PaymentsPage.test.tsx:133](../../apps/web/src/pages/payments/PaymentsPage.test.tsx#L133) |
| records a payment and shows field errors | [apps/web/src/pages/payments/PaymentsPage.test.tsx:151](../../apps/web/src/pages/payments/PaymentsPage.test.tsx#L151) |
| lists societies and shows the in-use block plainly | [apps/web/src/pages/reference/ReferencePage.test.tsx:51](../../apps/web/src/pages/reference/ReferencePage.test.tsx#L51) |
| creates a society and shows a field error from the API | [apps/web/src/pages/reference/ReferencePage.test.tsx:64](../../apps/web/src/pages/reference/ReferencePage.test.tsx#L64) |
| reorders reasons by sending every id | [apps/web/src/pages/reference/ReferencePage.test.tsx:79](../../apps/web/src/pages/reference/ReferencePage.test.tsx#L79) |
| saves a service | [apps/web/src/pages/reference/ReferencePage.test.tsx:92](../../apps/web/src/pages/reference/ReferencePage.test.tsx#L92) |
| saves one key and shows its validation message | [apps/web/src/pages/reference/ReferencePage.test.tsx:114](../../apps/web/src/pages/reference/ReferencePage.test.tsx#L114) |
| filters by entity and shows old and new values | [apps/web/src/pages/reference/ReferencePage.test.tsx:133](../../apps/web/src/pages/reference/ReferencePage.test.tsx#L133) |
| shows crew lanes, job cards, flags and the unscheduled reason | [apps/web/src/pages/schedule/SchedulePage.test.tsx:120](../../apps/web/src/pages/schedule/SchedulePage.test.tsx#L120) |
| moves a job by dropping it on another crew lane | [apps/web/src/pages/schedule/SchedulePage.test.tsx:139](../../apps/web/src/pages/schedule/SchedulePage.test.tsx#L139) |
| moves and takes a job off from its dialog | [apps/web/src/pages/schedule/SchedulePage.test.tsx:155](../../apps/web/src/pages/schedule/SchedulePage.test.tsx#L155) |
| shows a frozen-schedule conflict plainly and offers the code prompt | [apps/web/src/pages/schedule/SchedulePage.test.tsx:167](../../apps/web/src/pages/schedule/SchedulePage.test.tsx#L167) |
| freezes a draft after a confirmation | [apps/web/src/pages/schedule/SchedulePage.test.tsx:181](../../apps/web/src/pages/schedule/SchedulePage.test.tsx#L181) |
| unfreezes with the code and shows a wrong code inside the prompt | [apps/web/src/pages/schedule/SchedulePage.test.tsx:190](../../apps/web/src/pages/schedule/SchedulePage.test.tsx#L190) |
| runs the scheduler with the chosen period and lists needs scheduling | [apps/web/src/pages/schedule/SchedulePage.test.tsx:212](../../apps/web/src/pages/schedule/SchedulePage.test.tsx#L212) |
| shows demand against capacity and marks over capacity dates | [apps/web/src/pages/schedule/SchedulePage.test.tsx:226](../../apps/web/src/pages/schedule/SchedulePage.test.tsx#L226) |
| saves email opt-out and retains unsaved edits during external refresh | [apps/web/src/pages/settings/AlertEmailSettings.test.tsx:9](../../apps/web/src/pages/settings/AlertEmailSettings.test.tsx#L9) |
| open queries refetch external writes on the shared cadence | [apps/web/src/pages/settings/AlertEmailSettings.test.tsx:28](../../apps/web/src/pages/settings/AlertEmailSettings.test.tsx#L28) |
| starts disabled, requires a time to enable and saves the IST setting | [apps/web/src/pages/settings/AutomaticPlanningSettings.test.tsx:8](../../apps/web/src/pages/settings/AutomaticPlanningSettings.test.tsx#L8) |
| allows only the moves the API accepts | [apps/web/src/pages/subscriptions/SubscriptionsPage.test.tsx:40](../../apps/web/src/pages/subscriptions/SubscriptionsPage.test.tsx#L40) |
| lists subscriptions and activates one with a first service date | [apps/web/src/pages/subscriptions/SubscriptionsPage.test.tsx:46](../../apps/web/src/pages/subscriptions/SubscriptionsPage.test.tsx#L46) |
| explains a missing list endpoint and still offers the ID form | [apps/web/src/pages/subscriptions/SubscriptionsPage.test.tsx:73](../../apps/web/src/pages/subscriptions/SubscriptionsPage.test.tsx#L73) |
| requires a reason for Inactive and shows the API error | [apps/web/src/pages/subscriptions/SubscriptionsPage.test.tsx:80](../../apps/web/src/pages/subscriptions/SubscriptionsPage.test.tsx#L80) |
| skips a day on behalf of the customer | [apps/web/src/pages/subscriptions/SubscriptionsPage.test.tsx:99](../../apps/web/src/pages/subscriptions/SubscriptionsPage.test.tsx#L99) |
| shows complaint vehicle/photos and the linked visit proof | [apps/web/src/pages/support/support.test.tsx:72](../../apps/web/src/pages/support/support.test.tsx#L72) |
| merges both sources, tagged, and marks one read on its own endpoint | [apps/web/src/pages/support/support.test.tsx:87](../../apps/web/src/pages/support/support.test.tsx#L87) |
| reads all on both sources | [apps/web/src/pages/support/support.test.tsx:101](../../apps/web/src/pages/support/support.test.tsx#L101) |
| shows the unread count on the bell | [apps/web/src/pages/support/support.test.tsx:112](../../apps/web/src/pages/support/support.test.tsx#L112) |
| shows the four counts | [apps/web/src/pages/support/support.test.tsx:122](../../apps/web/src/pages/support/support.test.tsx#L122) |
| marks overdue rows and filters by status on the server | [apps/web/src/pages/support/support.test.tsx:140](../../apps/web/src/pages/support/support.test.tsx#L140) |
| sets the status and adds a note on the detail page | [apps/web/src/pages/support/support.test.tsx:149](../../apps/web/src/pages/support/support.test.tsx#L149) |
| shows ratings tag counts and check-in averages | [apps/web/src/pages/support/support.test.tsx:170](../../apps/web/src/pages/support/support.test.tsx#L170) |
| adds and deactivates a category | [apps/web/src/pages/support/support.test.tsx:195](../../apps/web/src/pages/support/support.test.tsx#L195) |
