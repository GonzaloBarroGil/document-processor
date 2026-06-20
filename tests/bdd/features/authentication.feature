Feature: Authentication
  As a system operator
  I want all API access to require an API key
  So that only authorized clients can submit and retrieve documents

  Scenario: Valid API key
    Given client provides header X-API-Key with a valid key
    When client makes any request
    Then the request is processed normally

  Scenario: Missing API key
    Given client does not provide the X-API-Key header
    When client makes any request
    Then the response status is 401

  Scenario: Invalid API key
    Given client provides an invalid or revoked API key
    When client makes any request
    Then the response status is 403

  Scenario: Health endpoint bypasses auth
    Given any client
    When GET /health is called without an API key
    Then the response status is 200
