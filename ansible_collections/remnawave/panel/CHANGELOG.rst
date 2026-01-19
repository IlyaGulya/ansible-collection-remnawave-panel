=============================
Remnawave Panel Release Notes
=============================

.. contents:: Topics

v0.1.0
======

Release Summary
---------------

Initial release of the Remnawave Panel Ansible collection.

Major Changes
-------------

- Added ``config_profile`` module for managing configuration profiles.
- Added ``node`` module for managing nodes.
- Auto-generated from Remnawave Panel OpenAPI specification.

Minor Changes
-------------

- Standardized CI workflow to use ``setup-uv@v7`` consistently across all jobs.
- Added ``ansible-lint`` to dev dependencies.
- Added ``meta/runtime.yml`` for Ansible Galaxy compatibility (requires ansible >= 2.15.0).
- Fixed ansible-lint violations in example playbooks.
