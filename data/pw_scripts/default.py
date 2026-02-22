async def run(page, ctx, config):
    content_mode = config.get("content_mode", "html")
    selector = config.get("selector")

    if content_mode == "screenshot":
        return await ctx.screenshot(page, selector)

    if selector:
        ctx.select(selector)

    if content_mode == "download":
        return await ctx.download_images()

    return ctx.save_html()
