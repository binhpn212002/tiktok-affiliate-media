"""Run through Odoo shell with the environment of the video database."""

import time


def run_render_worker(environment):
    print("Local video render worker started. Press Ctrl+C to stop.", flush=True)
    while True:
        try:
            environment["affiliate.video"]._cron_render_video()
            environment.cr.commit()
            environment.invalidate_all(flush=False)
            time.sleep(3)
        except KeyboardInterrupt:
            environment.cr.rollback()
            print("Local video render worker stopped.", flush=True)
            return


run_render_worker(globals()["env"])
