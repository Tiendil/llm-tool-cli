# Behavior specification requirements

## Goal of the document

This document describes the content and abstraction level of behavior specifications.

## Scope

This specification applies to behavior specification documents under `specs/behavior/`.
General specification conventions and architecture specification content are out of scope.

## Abstraction level

Behavior specifications MUST describe observable behavior, input/output contracts, and failure semantics.
They MUST NOT specify implementation function or type names or type signatures, including those exposed through public Python interfaces.
Those details MAY be documented in architecture specifications or API documentation.

Stable externally visible representations, such as diagnostic codes and output field names, MAY be specified when they are part of the behavior contract.
