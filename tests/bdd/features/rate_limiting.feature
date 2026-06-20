Feature: Rate Limiting
  As a system operator
  I want to limit ingestion rate per client
  So that the system is protected from abuse and resource exhaustion

  Scenario: Client within rate limit
    Given client ABC has submitted 59 documents in the current minute
    When client ABC POSTs to /documents
    Then the response status is 202

  Scenario: Client exceeds rate limit
    Given client ABC has submitted 60 documents in the current minute
    When client ABC POSTs to /documents
    Then the response status is 429
    And the body contains "Rate limit exceeded"
    And the header "Retry-After" is present

  Scenario: Rate limit resets after window
    Given client ABC exceeded the rate limit at minute N
    When client ABC POSTs at minute N+1
    Then a new request is accepted

  Scenario: Rate limit is per authenticated client
    Given client ABC is at its limit
    When client XYZ POSTs to /documents
    Then client XYZ's request is accepted
