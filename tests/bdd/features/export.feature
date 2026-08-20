Feature: Export
  As an operator
  I want to export a document's extracted data
  So that it can be consumed by other systems

  Scenario: Export JSON
    Given a COMPLETED document
    When the operator requests export
    Then a flattened JSON payload is returned

  Scenario: Export CSV
    Given a COMPLETED document
    When the operator requests export with Accept: text/csv
    Then a CSV payload is returned
