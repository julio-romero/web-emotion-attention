from multimotions.core import DataProcessor
import matplotlib.pyplot as plt

def test_data_processor_creation():
    processor = DataProcessor("data/scroll_data.csv", "data/imotions_data.csv", "data/")
    assert processor is not None

def test_data_processing():
    processor = DataProcessor("data/scroll_data.csv", "data/imotions_data.csv", "data/")
    processor.process_data()
    assert processor.merged_data is not None


def test_create_heatmap():
    processor = DataProcessor("data/scroll_data.csv", "data/imotions_data.csv", "data/")
    processor.process_data()
    fig = processor.plot_heatmap() 
    plt.show()

if __name__ == "__main__":
    # test_data_processor_creation()
    # test_data_processing()
    test_create_heatmap()
