write_all_statistics:
	env PREFECT__FLOWS__CHECKPOINTING=true python3 scripts/write_all_statistics

upload:
	rm -rf dist && \
	python3 setup.py sdist bdist_wheel && \
	python3 -m twine check dist/* && \
	python3 -m twine upload dist/*
