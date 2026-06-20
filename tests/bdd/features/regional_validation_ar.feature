Feature: Regional Validation — Argentina
  As a system operating in Argentina
  I want to validate extracted invoice data against AFIP regulations
  So that only compliant documents are accepted

  Scenario: Valid AFIP invoice type A
    Given parsed data contains tipo_comprobante "A" and cuit_emisor "30-12345678-1"
    And the CAE number is present and properly formatted
    When the Argentina validator runs
    Then validation_result is "PASS"

  Scenario: Invalid CUIT format
    Given parsed data contains cuit_emisor "12-34-567"
    When the Argentina validator runs
    Then validation_result is "FAIL"
    And errors include field "cuit_emisor" with rule "CUIT_FORMAT"

  Scenario: Missing mandatory AFIP field
    Given parsed data is missing "cae" for an invoice type that requires it
    When the Argentina validator runs
    Then validation_result is "FAIL"
    And errors include field "cae" with rule "CAE_REQUIRED"
