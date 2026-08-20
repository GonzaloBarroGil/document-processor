Feature: Authentication
  As a web app user
  I want to log in with a username and password
  So that I can access my documents and the review queue

  Scenario: Successful login
    Given a user with role REVIEWER exists
    When they log in with valid credentials
    Then they receive an access token and a refresh token

  Scenario: Failed login
    Given a user enters an incorrect password
    When they attempt to log in
    Then the login response status is 401

  Scenario: Access token refresh
    Given a user has a valid refresh token
    When they exchange the refresh token for a new pair
    Then they receive a new access token
