# openwrt-iac project site + apk feed

This repo holds two things on one `gh-pages` branch:

- the **public site** at <https://openwrt-iac.github.io/> (landing page, install instructions, OpenAPI reference)
- the **signed apk feed** at <https://openwrt-iac.github.io/feed/packages/all/uapi/packages.adb>, aggregating stable releases from the project's OpenWrt-package repos

## Layout (main branch)

```
web/              static site source (HTML + CSS)
keys/             public key file served from the feed
feed.yml          list of source repos + asset patterns
scripts/          helpers invoked by the publish workflow
.github/
  workflows/
    publish.yml   one workflow that rebuilds gh-pages from all three inputs
```

## Adding a new package to the feed

PR a one-liner block to `feed.yml`:

```yaml
sources:
  - repo: openwrt-iac/<your-package>
    asset_pattern: '<your-package>-*.apk'
```

Requirements on the source repo:

- Each `v*` tag attaches the built APK as a release asset matching `asset_pattern`.
- Prerelease tags (anything containing a hyphen, e.g. `v1.0.0-rc1`) are marked `--prerelease` on the GitHub Release. The aggregator filters with `gh release list --exclude-pre-releases`; nothing further is required.

After merge, the next nightly run (or a manual `gh workflow run publish.yml --repo openwrt-iac/openwrt-iac.github.io`) picks up the new package's latest stable release and republishes the feed index.

## Operator install

```
curl -fsSL https://openwrt-iac.github.io/feed/uapi-feed.pub.pem \
    | tee /etc/apk/keys/uapi-feed.pub.pem > /dev/null
echo 'https://openwrt-iac.github.io/feed/packages/all/uapi/packages.adb' \
    > /etc/apk/repositories.d/uapi.list
apk update
apk add uapi
apk add unbound-uci-ext   # or any other package this feed hosts
```

## Trust model

- Feed signing key (`uapi-feed.pub.pem`) is RSA-4096 PEM-encoded.
- The private half lives in this repo's `FEED_SIGNING_KEY` secret and is never written to a runner's filesystem outside the publish job's transient `mktemp`-d location.
- Source-repo authenticity is GitHub's: the aggregator only pulls release assets from the repos listed in `feed.yml`. If you trust those repos, you trust the apks they emit.
