# Changelog

All notable changes to the mn_payments app will be documented in this file.

## [1.0.0] - 2025-01-XX

### Added
- **QPay Integration**
  - QR invoice generation using official qpay_client library (>=0.3.2)
  - Real-time payment status checking
  - Automatic payment callback handling with guest access
  - Payment Request synchronization with ERPNext
  - Qpay Invoice DocType for complete audit trail
  - Configurable sandbox mode for testing

- **Ebarimt Tax Authority Integration**
  - PosAPI receipt submission to Mongolia tax authority
  - TPI taxpayer information lookup service
  - Cached district code reference data
  - Pharmacy mode support with specialized handling
  - Automatic city tax calculation (1% on alcohol, tobacco, fuel)
  - VAT allocation (10% standard rate)

- **POS Integration**
  - Automatic receipt submission on POS Invoice submit
  - Auto Submit on POS Invoice enabled by default
  - Item group-based city tax detection (Alcohol, Tobacco, Petroleum Products)
  - Tax calculation from invoice items and taxes

- **Configuration**
  - Qpay Settings (Single DocType) with UI access
  - Ebarimt Settings (Single DocType) with UI access
  - Dropdown URL selection (Production/Staging/Custom)
  - Conditional mandatory fields based on enabled status
  - Fallback to site_config.json for backwards compatibility

- **API Endpoints**
  - `/api/method/mn_payments.api.qpay.*` endpoints
  - `/api/method/mn_payments.api.ebarimt.*` endpoints
  - Legacy compatibility shims for existing imports

- **Testing**
  - 35 comprehensive unit tests
  - Coverage for QPay utilities and API
  - Coverage for Ebarimt utilities and API
  - Test fixtures and mocks for external services

### Dependencies
- frappe (framework)
- qpay-client>=0.3.2 (official QPay library)
- requests>=2.25.0 (HTTP client)
- erpnext (for POS Invoice integration)

### Technical Details
- **Hooks**: doc_events for POS Invoice on_submit
- **Caching**: District codes and tokens cached in Frappe cache
- **Error Handling**: Comprehensive error guards on all API endpoints
- **Backward Compatibility**: Legacy import paths supported via shims

### Breaking Changes
None - initial release

### Known Issues
None

---

## Future Roadmap

### Planned Features
- [ ] QPay refund processing
- [ ] Ebarimt receipt cancellation/correction
- [ ] Multi-currency support for QPay
- [ ] Dashboard widgets for payment/receipt statistics
- [ ] Scheduled background jobs for payment verification
- [ ] Email notifications for payment events
- [ ] Webhook retry logic with exponential backoff

### Under Consideration
- [ ] Support for additional Mongolian payment gateways
- [ ] Integration with ERPNext Accounting module for automatic journal entries
- [ ] Custom report for tax compliance
- [ ] Bulk receipt submission API
