from pipeline.unpackDB.unpack import run

def main():
    config_path = "scratch/new_fmt_conbined.json"
    result = run(config_path)
    print(result)

if __name__ == "__main__":
    main()