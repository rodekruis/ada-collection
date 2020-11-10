from ada_tools.get_images_maxar import get_maxar_image_urls

def test_get_maxar_image_urls():
    """
    If this test fails, it means that either:
    - The page layout or url scheme of Maxar's open data changed.
    - The 2020 Mauritius oil spill that we use for testing has been removed from
      opendata.
    """
    expected_urls = [
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-08-08/102001009AE32600/102001009AE32600.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-08-08/102001009B8D4A00/102001009B8D4A00.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-08-12/10300100AC17E200/10300100AC17E200.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-08-12/10300100AC83F700/10300100AC83F700.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-08-12/105001001F1B5B00/105001001F1B5B00.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-08-13/104001006029DF00/104001006029DF00.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-09-07/102001009F9BF300/102001009F9BF300.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-09-08/104001006034F900/104001006034F900.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-09-11/1020010098A8BD00/1020010098A8BD00.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-09-11/102001009ED50300/102001009ED50300.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-09-14/10300100AB177A00/10300100AB177A00.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-09-14/10300100AB196B00/10300100AB196B00.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-09-14/10300100AC291900/10300100AC291900.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-09-14/104001005F192C00/104001005F192C00.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-09-14/105001001FA87D00/105001001FA87D00.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-09-14/105001001FA87E00/105001001FA87E00.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/post-event/2020-10-16/104001006131E200/104001006131E200.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/pre-event/2020-07-16/10300100AA8C8400/10300100AA8C8400.tif",
        "https://opendata.digitalglobe.com/events/mauritius-oil-spill/pre-event/2020-07-16/10300100AA94E000/10300100AA94E000.tif",
    ]

    urls = get_maxar_image_urls("mauritius-oil-spill")
    assert sorted(urls) == sorted(expected_urls)
