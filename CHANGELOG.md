# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- First release.
- `KeyedLock`: per-key locking with reference-counted table cleanup and an optional
  reentrant mode.
- `StripedLock`: a fixed pool of locks that caps memory for large or unbounded key spaces.
