"""Replace BigInteger with Integer in all model files for SQLite compatibility."""
import os
import glob

model_dir = os.path.join(os.path.dirname(__file__), 'app', 'models')
for filepath in glob.glob(os.path.join(model_dir, '*.py')):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'BigInteger' not in content:
        continue
    # Replace in imports: BigInteger, -> Integer,
    content = content.replace('BigInteger,', 'Integer,')
    # Replace in mapped_column: BigInteger -> Integer
    content = content.replace('BigInteger)', 'Integer)')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Fixed: {filepath}')
print('Done.')
