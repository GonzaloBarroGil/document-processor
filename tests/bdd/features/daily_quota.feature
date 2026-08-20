Feature: Cost controls
  As a system operator
  I want ingestion bounded by a daily quota
  So that a public API cannot drive unbounded cost

  Scenario: Within daily quota
    Given the global daily count is below the cap
    When a client ingests a document
    Then the response is accepted

  Scenario: Daily quota exceeded
    Given the global daily cap has been reached
    When a client ingests a document
    Then the response is 429
