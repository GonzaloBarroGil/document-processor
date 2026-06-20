Feature: Document Ingestion
  As a mobile app
  I want to submit an image of a payment document
  So that it can be processed and the extracted data retrieved later

  Scenario: Submit a valid invoice image as JPEG
    Given a valid JPEG image of an invoice under 10MB
    When I POST to /documents with the image, type "invoice", and region "AR"
    Then the response status is 202
    And the response contains a document_id
    And the status is "PENDING"

  Scenario: Submit a valid ticket as HEIC
    Given a valid HEIC image of a ticket under 10MB
    When I POST to /documents
    Then the response status is 202

  Scenario: Submit a PDF invoice
    Given a valid PDF document under 10MB
    When I POST to /documents with type "invoice"
    Then the response status is 202
    And the system will rasterize it for OCR

  Scenario: Submit an unsupported file type
    Given a file of type "application/x-tar"
    When I POST to /documents
    Then the response status is 422
    And the body contains "Unsupported media type"

  Scenario: Submit an image exceeding size limit
    Given a JPEG image of 15MB
    When I POST to /documents
    Then the response status is 413
    And the body contains "File too large"
