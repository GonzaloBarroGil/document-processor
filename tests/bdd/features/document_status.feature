Feature: Document Status Retrieval
  As a mobile app
  I want to check the processing status of a submitted document
  So that I can show the user progress

  Scenario: Check status of a completed document
    Given a document with id "doc-123" exists and status is "COMPLETED"
    When I GET /documents/doc-123
    Then the response status is 200
    And the body contains status "COMPLETED"
    And the body includes parsed_data with extracted fields
    And the body includes validation_result with pass/fail

  Scenario: Check status of a non-existent document
    Given no document with id "unknown-id" exists
    When I GET /documents/unknown-id
    Then the response status is 404

  Scenario: Check status of a document still processing
    Given a document with id "doc-456" has status "OCR_IN_PROGRESS"
    When I GET /documents/doc-456
    Then the response status is 200
    And the body contains status "OCR_IN_PROGRESS"
    And parsed_data is null
