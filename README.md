# openwrt-iac project site + apk feed

This repo holds two things on one `gh-pages` branch:

- the **public site** at <https://openwrt-iac.github.io/>: a landing page for the openwrt-iac project (the effort to make OpenWrt as Infrastructure-as-Code-capable as possible) plus a sub-tree per project under it (currently <https://openwrt-iac.github.io/uapi/>).
- the **signed apk feed** at <https://openwrt-iac.github.io/feed/packages/all/uapi/packages.adb>, aggregating stable releases from every openwrt-iac package repo.

## Layout (main branch)

```
web/
  index.html                project landing (openwrt-iac org mission, links to subprojects)
  style.css                 shared stylesheet for every page on the site
  uapi/
    index.html              uapi project landing
    install/index.html      uapi install + first-token walkthrough
    api/index.html          Redoc-rendered OpenAPI reference
keys/                       public key file served from the feed
feed.yml                    list of source repos + asset patterns
scripts/                    helpers invoked by the publish workflow
.github/
  workflows/
    publish.yml             one workflow that rebuilds gh-pages from all inputs
```

Internal HTML links are absolute paths from the site root (`/style.css`, `/uapi/install/`, `/feed/...`) so future page moves don't churn the link graph.

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

If your new package is substantial enough to warrant a project page (and it usually is, otherwise consider whether it belongs in this org), add a `web/<package>/index.html` mirroring the `web/uapi/` shape and link it from `web/index.html`'s "projects" section.

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
