app_name = "mn_payments"
app_title = "MN Payments"
app_publisher = "Custom"
app_description = "Mongolian payment + ebarimt integration (minimal)"
app_email = "dev@example.com"
app_license = "MIT"
app_version = "0.1.0"

required_apps = ["frappe"]

doc_events = {
	"Payment Transaction": {
		"on_cancel": "mn_payments.ebarimt.tasks.scrub_individuals",
	},
}

scheduler_events = {
	"hourly": [
		"mn_payments.ebarimt.tasks.scrub_individuals",
	],
}
