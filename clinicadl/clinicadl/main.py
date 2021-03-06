# coding: utf8

import torch

from . import cli


def main():

    parser = cli.parse_command_line()
    args = parser.parse_args()

    if args.version:
        import clinicadl

        print(f"ClinicaDL version is: {clinicadl.__version__}")
        exit(0)
    if hasattr(args, "use_cpu"):
        if (
            args.use_cpu is not None
            and not args.use_cpu
            and not torch.cuda.is_available()
        ):
            raise ValueError(
                "No GPU is available. Please add the -cpu flag to run on CPU."
            )
    if hasattr(args, "use_gpu"):
        if args.use_gpu and torch.cuda.is_available():
            raise ValueError(
                "No GPU is available. Please disable -gpu flag to run on CPU."
            )

    if not args.task:
        parser.print_help()
    else:
        args.func(args)


if __name__ == "__main__":
    main()
