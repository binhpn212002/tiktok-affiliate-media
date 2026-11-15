{
    "name": "TikTok Affiliate Studio",
    "version": "17.0.1.3.0",
    "category": "Marketing",
    "summary": "Manage TikTok affiliate campaigns and video production",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/affiliate_channel_views.xml",
        "views/affiliate_product_views.xml",
        "views/affiliate_campaign_views.xml",
        "views/affiliate_video_views.xml",
        "data/video_render_cron.xml",
        "data/tiktok_oauth_cron.xml",
        "views/affiliate_post_task_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "tiktok_affiliate_studio/static/src/fields/product_images.js",
            "tiktok_affiliate_studio/static/src/fields/product_images.xml",
        ],
    },
    "application": True,
    "installable": True,
    "license": "LGPL-3",
}
