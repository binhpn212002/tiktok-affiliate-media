def migrate(cr, version):
    cr.execute("ALTER TABLE affiliate_video DROP COLUMN IF EXISTS template_id")
