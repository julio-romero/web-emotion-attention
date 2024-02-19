from multimotions.core import DataProcessor


def test_data_processor():
    processor = DataProcessor("target", None, "target")
    try:
        processor.start_monitoring(5)
    except KeyboardInterrupt:
        processor.plot_data()

if __name__ == "__main__":
    test_data_processor()