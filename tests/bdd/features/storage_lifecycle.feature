Feature: Storage Lifecycle
  As a system operator
  I want old images to be auto-deleted when storage pressure is high
  So that storage costs are controlled without manual intervention

  Scenario: Storage below high-water mark
    Given storage usage is under 80 percent of the configured limit
    When the storage lifecycle job runs
    Then no images are deleted

  Scenario: Storage exceeds high-water mark with alert acknowledged
    Given storage usage reaches 85 percent
    And an alert was sent to operators
    And an operator acknowledged the alert
    Then images are not auto-deleted

  Scenario: Storage exceeds high-water mark with alert unattended
    Given storage usage reaches 85 percent
    And 72 hours have passed without acknowledgment
    When the storage lifecycle job runs
    Then images for COMPLETED documents older than 90 days are deleted
    And the document record status becomes "IMAGE_EXPIRED"
    And parsed_data is preserved in the database

  Scenario: Retrieving an expired document
    Given a document has status "IMAGE_EXPIRED"
    When GET /documents/{id}/image is called
    Then the response status is 410
    But GET /documents/{id} still returns the document with parsed_data intact
