Feature: Pluggable Regional Validation
  As a system operator
  I want to add new regional validation modules without modifying the core
  So that the system can expand to new countries

  Scenario: Load all registered validators at startup
    Given validators are registered for "AR" and "BR"
    When the application starts
    Then both validators are loaded and discoverable by region code

  Scenario: Unknown region falls back gracefully
    Given no validator is registered for "XX"
    When a document is submitted with region "XX"
    Then the document is processed without validation
    And validation_result is marked as "SKIPPED"

  Scenario: Add a new region validator deployment
    Given a new validator module for region "UY" is added as a plugin
    When the application restarts
    Then the validator is auto-discovered and operational
