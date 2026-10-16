from image_workflow.stickers import make_stickers


def test_local_stickers_have_four_transparent_variants():
    stickers = make_stickers()
    assert len(stickers) == 4
    assert all(image.size == (320, 420) and image.mode == "RGBA" for image in stickers)
    assert all(image.getpixel((0, 0))[3] == 0 for image in stickers)
    assert all(image.getchannel("A").getbbox() for image in stickers)
    assert len({image.tobytes() for image in stickers}) == 4
