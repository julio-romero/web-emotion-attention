from multimotions.core import DataProcessor

def test_data_processor_creation():
    processor = DataProcessor("data/scroll_data.csv", "data/imotions_data.csv", "data/")
    assert processor is not None

def test_data_processing():
    processor = DataProcessor("data/scroll_data.csv", "data/imotions_data.csv", "data/")
    processor.process_data()
    assert processor.merged_data is not None


if __name__ == "__main__":
    test_data_processor_creation()
    test_data_processing()
