from evaluations.g5k_expe.g5k_expe import G5KExpe


def main():
    expe = G5KExpe(
        topology_conf="./relays.yaml",
    )


if __name__ == "__main__":
    main()
