import numpy as np
import pandas as pd
import torch
from torch.nn.functional import softmax

from clinicadl.utils.task_manager.task_manager import TaskManager


class ClassificationManager(TaskManager):
    def __init__(
        self,
        mode,
    ):
        super().__init__(mode)

    @property
    def columns(self):
        return [
            "participant_id",
            "session_id",
            f"{self.mode}_id",
            "true_label",
            "predicted_label",
            "proba0",
            "proba1",
        ]

    @property
    def evaluation_metrics(self):
        return ["accuracy", "sensitivity", "specificity", "PPV", "NPV", "BA"]

    def generate_test_row(self, idx, data, outputs):

        predicted = torch.argmax(outputs[idx].data)
        normalized_output = softmax(outputs[idx], dim=1)
        return [
            [
                data["participant_id"][idx],
                data["session_id"][idx],
                data[f"{self.mode}_id"][idx].item(),
                data["label"][idx].item(),
                predicted[idx].item(),
                normalized_output[0].item(),
                normalized_output[1].item(),
            ]
        ]

    def compute_metrics(self, results_df):
        return self.metrics_module.apply(
            results_df.true_label.values,
            results_df.predicted_label.values,
        )

    @staticmethod
    def generate_label_code(df, label):
        unique_labels = list(set(getattr(df, label)))
        unique_labels.sort()
        return {key: value for value, key in enumerate(unique_labels)}

    @staticmethod
    def output_size(input_size, df, label):
        label_code = ClassificationManager.generate_label_code(df, label)
        return len(label_code)

    def ensemble_prediction(
        self,
        performance_df,
        validation_df,
        selection_threshold=None,
        use_labels=True,
        method="soft",
    ):
        """
        Computes hard or soft voting based on the probabilities in performance_df. Weights are computed based
        on the balanced accuracies of validation_df.

        ref: S. Raschka. Python Machine Learning., 2015

        Args:
            performance_df (pd.DataFrame): results that need to be assembled.
            validation_df (pd.DataFrame): results on the validation set used to compute the performance
                of each separate part of the image.
            selection_threshold (float): with soft-voting method, allows to exclude some parts of the image
                if their associated performance is too low.
            use_labels (bool): If True, metrics are computed and the label column values must be different
                from None.
            method (str): method to assemble the results. Current implementation proposes soft or hard-voting.

        Returns:
            df_final (pd.DataFrame) the results on the image level
            results (Dict[str, float]) the metrics on the image level
        """

        def check_prediction(row):
            if row["true_label"] == row["predicted_label"]:
                return 1
            else:
                return 0

        if method == "soft":
            # Compute the sub-level accuracies on the validation set:
            validation_df["accurate_prediction"] = validation_df.apply(
                lambda x: check_prediction(x), axis=1
            )
            sub_level_accuracies = validation_df.groupby(f"{self.mode}_id")[
                "accurate_prediction"
            ].mean()
            if selection_threshold is not None:
                sub_level_accuracies[sub_level_accuracies < selection_threshold] = 0
            weight_series = sub_level_accuracies / sub_level_accuracies.sum()
        elif method == "hard":
            n_modes = validation_df[f"{self.mode}_id"].nunique()
            weight_series = pd.DataFrame(np.ones((n_modes, 1)))
        else:
            raise NotImplementedError(
                f"Ensemble method {method} was not implemented. "
                f"Please choose in ['hard', 'soft']."
            )

        # Sort to allow weighted average computation
        performance_df.sort_values(
            ["participant_id", "session_id", f"{self.mode}_id"], inplace=True
        )
        weight_series.sort_index(inplace=True)

        # Soft majority vote
        df_final = pd.DataFrame(columns=self.columns)
        for (subject, session), subject_df in performance_df.groupby(
            ["participant_id", "session_id"]
        ):
            label = subject_df["true_label"].unique().item()
            proba0 = np.average(subject_df["proba0"], weights=weight_series)
            proba1 = np.average(subject_df["proba1"], weights=weight_series)
            proba_list = [proba0, proba1]
            prediction = proba_list.index(max(proba_list))
            row = [[subject, session, 0, label, prediction, proba0, proba1]]
            row_df = pd.DataFrame(row, columns=self.columns)
            df_final = df_final.append(row_df)

        if use_labels:
            results = self.compute_metrics(df_final)
        else:
            results = None

        return df_final, results
