from multimotions.core import DataProcessor


def test_data_processor():
    processor = DataProcessor("data/scroll_data.csv", "data/imotions_data.csv", "data/")
    assert processor is not None
    processor.process_data()


if __name__ == "__main__":
    test_data_processor()