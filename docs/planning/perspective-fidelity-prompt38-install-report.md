# Prompt38 install provenance

The isolated candidate at `/private/tmp/neural-showdown-native11-prompt38/sim-core` now pins `pokemon-showdown` to exact `0.11.11`. The approved local artifact `/private/tmp/neural-prompt29-20261012/0.11.11.tgz` was verified before installation: SHA-256 `49af14aaed1084887f756372c7386c9987905930cc848ed31e9202c10c592d66`, SHA-1 `2b2f877df641a231a0078512505c9a84a39084a7`, and SRI `sha512-FdW7gt3TkG4AdXmpMTPYX2kx42VEfY8tQApjW9wEHOGzwH6Kn97wD0o5uIzAc4xpO1W+Tim70Ti9+FNkMNCA2w==`. Prompt29 registry metadata records version `0.11.11` and `gitHead` `739a5e1fee432ad80ff7136d70cca993be358b59`; the tag metadata resolves to the same revision.

Installation began with lifecycle scripts disabled. The tarball ships compiled `dist/` JavaScript, declarations, and the `build` artifact, so a lifecycle build was unnecessary. The first attempt was stopped at the required 180-second process-group deadline because sandbox DNS could not resolve registry manifests. A single elevated retry using the verified local tarball completed with `added 186 packages in 7s`; npm emitted deprecation warnings for legacy transitive packages. A subsequent `npm install --package-lock-only --ignore-scripts --no-audit --no-fund` completed successfully and reconciled the lock to registry URLs and integrity values.

The candidate lock has 213 package records. The target lock entry is:

```text
pokemon-showdown 0.11.11
https://registry.npmjs.org/pokemon-showdown/-/pokemon-showdown-0.11.11.tgz
sha512-FdW7gt3TkG4AdXmpMTPYX2kx42VEfY8tQApjW9wEHOGzwH6Kn97wD0o5uIzAc4xpO1W+Tim70Ti9+FNkMNCA2w==
```

The installed `node_modules/pokemon-showdown/package.json` is byte-identical to the tar member. `npm ls --all --omit=dev --ignore-scripts` reports no problems, and all 11 target optional direct dependencies are present in this macOS tree. Compared with the original 0.11.10 lock, the resolved graph changes from 202 to 213 package records, with 57 added paths, 46 removed paths, and 68 changed paths. Material direct upgrades include esbuild `0.16.17 → 0.25.12`, preact-render-to-string `5.2.6 → 6.8.0`, better-sqlite3 `7.6.2 → 11.10.0`, nodemailer `6.10.1 → 7.0.13`, sqlite `3.0.6 → 5.1.1`, and sqlite3 `4.2.0 → 5.1.7`; native/optional ABI behavior remains outside this installation lane.

Candidate manifest hash: `914ef9d28ca6179dbc95bc0027228b5d4e913b98e58f7e76c27f93fd1ed8de72`.

Candidate lock hash: `04eebf417864707d3a3322d6371e811fda3d2fff3c95995d44a4aaf579724c88`.

The original checkout dependency files remain unchanged: `sim-core/package.json` SHA-256 `1a81e29560c44c3997437e4f2cf22e2312e71e32448f600394dd5c0d1413f3f4`, and `sim-core/package-lock.json` SHA-256 `4897b92e6a6c82db2b8fe5cedb69c9b15386a0bff4d8d2a30b7a2c6d1d9a33c5`.

No candidate build, simulator import, test, generation, or canary was run by this lane.
