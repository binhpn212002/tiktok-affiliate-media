# tiktok-affiliate-media

Odoo 17 addon for TikTok Affiliate Studio. See the [MVP specification](docs/mvp.md) and [task index](docs/tasks/README.md).

See [video import, TTS, and rendering](docs/video-render-workflow.md) for setup and a sample script.

## Product images on R2

Install `boto3` in the Odoo Python environment. Provide these environment variables to the Odoo process and restart it:

- `R2_ENDPOINT_URL` — R2 S3 API endpoint.
- `R2_BUCKET` — bucket name.
- `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY` — credentials with write access to the bucket.
- `R2_PUBLIC_BASE_URL` — HTTPS URL of the bucket's public domain used to read images.

In **Products**, click **Add images**, select one or more files, and save the product. Odoo uploads JPEG, PNG, or WebP files up to 10 MB and stores each URL in `affiliate_product_image`. Removing a row removes the product's URL reference. Objects can be shared by multiple products and stay in R2.

## TikTok Login Kit

1. Configure a TikTok for Developers app with Login Kit for Web and the scopes `user.info.basic`, `user.info.profile`, and `user.info.stats`.
2. Register the exact HTTPS redirect URI `https://your-odoo-host/tiktok/oauth/callback`. Open Odoo on that same HTTPS host when connecting so the callback receives the Odoo session cookie. The HTTPS host must route to the database containing TikTok Affiliate Studio. Suppress query strings for the callback in reverse-proxy access logs.
3. Set `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, and `TIKTOK_REDIRECT_URI` in the Odoo process environment. The local `.env` is Git-ignored and must be loaded when starting Odoo.
4. Open a record under **Channels**, click **Connect TikTok**, and grant access on TikTok. **Sync TikTok** refreshes the profile on demand. A scheduled action also updates profiles and refreshes tokens near expiry. If TikTok revokes or expires a refresh token, connect again.

See [Login Kit for Web](https://developers.tiktok.com/docs/en/login-kit-web) and [User Info scopes](https://developers.tiktok.com/docs/en/tiktok-api-v2-get-user-info).
