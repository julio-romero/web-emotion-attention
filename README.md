# web-emotion-attention
Code used for the Neuromarketing project 

# Usage

```python
>>> from multimotions.core import DataProcessor
>>> processor = DataProcessor('web-data','imotions-data','data')
>>> processor.start_monitoring(5)

>>> processor.plot_data() # View the heatmap of the webpage 
```