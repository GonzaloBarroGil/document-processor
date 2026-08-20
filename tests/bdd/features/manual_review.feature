Feature: Manual review
  As a reviewer
  I want to correct and approve extracted fields
  So that bad extractions don't propagate downstream

  Scenario: Approve a document with corrected fields
    Given a document is in the review queue
    When the reviewer edits parsed fields and approves
    Then the document is marked reviewed

  Scenario: Request changes
    Given a document is in the review queue
    When the reviewer requests changes with a comment
    Then the document is flagged for re-extraction
