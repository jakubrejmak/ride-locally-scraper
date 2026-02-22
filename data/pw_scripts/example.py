async def run(page, ctx, config):
    await page.click("#accept-cookies")
    await page.click("#show-timetable")
    await page.wait_for_selector("#timetable")
    ctx.reload(await page.content())
    ctx.select("#timetable").select(".active-tab")
    return await ctx.download_images()
