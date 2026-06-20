Feature: OCR Processing
  As the system
  I want to extract text from document images
  So that structured data can be derived

  Background:
    Given the OCR engine is available

  Scenario: Extract text from a clear invoice
    Given a well-lit, high-resolution invoice image in Spanish
    When the OCR pipeline processes it
    Then raw text is extracted with confidence at least 0.7
    And fields "total_amount", "date", "vendor_name" are identifiable

  Scenario: Handle HEIC image
    Given a valid HEIC image
    When the OCR pipeline processes it
    Then the image is transcoded to JPEG or PNG before OCR
    And OCR proceeds on the transcoded image
    And the original HEIC is stored

  Scenario: Handle multi-page PDF
    Given a PDF with 3 pages
    When the OCR pipeline processes it
    Then each page is rasterized and OCRd
    And extracted text is merged from all pages

  Scenario: Handle unreadable image
    Given a blurry, low-resolution image
    When the OCR pipeline processes it
    Then the document status is set to "OCR_FAILED"
    And an error detail "Low confidence extraction" is recorded

  Scenario: Handle OCR engine timeout
    Given the OCR engine takes longer than 60 seconds
    When the OCR pipeline processes it
    Then the document status is set to "OCR_FAILED"

  Scenario: Handle HEIC transcoding failure
    Given a malformed HEIC file that cannot be transcoded
    When the OCR pipeline processes it
    Then the document status is set to "OCR_FAILED"
    And the error detail is "HEIC transcoding failed"
