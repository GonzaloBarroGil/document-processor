Feature: List Documents
  As a mobile app
  I want to list previously submitted documents
  So that the user can browse their history

  Scenario: List documents with pagination
    Given 25 documents exist in the system
    When I GET /documents with page 1 and size 10
    Then the response status is 200
    And the body contains 10 items
    And the body contains total 25
    And the body contains pages 3

  Scenario: Filter documents by status
    Given 5 PENDING and 10 COMPLETED documents exist
    When I GET /documents with status "COMPLETED"
    Then the response status is 200
    And all returned items have status "COMPLETED"
